"""
POST /recommend — generate investigation recommendations for a complaint.
POST /recommend
Accepts { "text": "..." } and returns 3 structured compliance recommendations.

Response shape:
{
  "recommendations": [
    {
      "action_type": "...",
      "description": "...",
      "priority": "High | Medium | Low"
    },
    ...
  ]
}
"""

import logging
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify

from middleware import sanitize_input
from helpers import extract_json, validate_required_fields
from services.groq_client import call_groq, load_prompt
from services.cache import make_cache_key, cache_get, cache_set
from services.vector_store import query_knowledge
from services.metrics import track

logger = logging.getLogger(__name__)

recommend_bp = Blueprint("recommend", __name__, url_prefix="/recommend")

_ITEM_FIELDS = ["action_type", "description", "priority", "responsible_party"]


def _fallback_recommendations() -> dict:
    """Return 3 generic recommendations when the AI is unavailable."""
    now = datetime.now(timezone.utc).isoformat()
    items = [
        {
            "action_type": "Document",
            "description": "Log the complaint details in the ethics case management system for record-keeping.",
            "priority": "Immediate",
            "responsible_party": "Ethics Committee",
            "generated_at": now,
            "is_fallback": True,
            "cache_hit": False,
        },
        {
            "action_type": "Escalate",
            "description": "Escalate the report to the senior compliance officer for initial review and triage.",
            "priority": "Within 24 Hours",
            "responsible_party": "Legal Team",
            "generated_at": now,
            "is_fallback": True,
            "cache_hit": False,
        },
        {
            "action_type": "Investigate",
            "description": "Assign an impartial investigator to conduct preliminary fact-finding interviews.",
            "priority": "Within 1 Week",
            "responsible_party": "HR Department",
            "generated_at": now,
            "is_fallback": True,
            "cache_hit": False,
        },
    ]
    return {
        "recommendations": items,
        "generated_at": now,
        "is_fallback": True,
        "cache_hit": False,
    }


@recommend_bp.route("/", methods=["POST"])
@track("/recommend")
def recommend():
    # 1. Validate Content-Type
    if not request.is_json:
        return (
            jsonify(
                {
                    "error": "Unsupported media type",
                    "message": "Content-Type must be application/json",
                }
            ),
            415,
        )

    # 2. Validate body
    data = request.get_json(silent=True) or {}
    text = data.get("text", "")
    if not text or not isinstance(text, str) or text.strip() == "":
        return (
            jsonify({"error": "Bad request", "message": "Field 'text' is required and must be a non-empty string."}),
            400,
        )

    # 3. Sanitise & injection check
    sanitized_text, is_injection = sanitize_input(text)
    if is_injection:
        return (
            jsonify(
                {
                    "error": "Bad request",
                    "message": "Potential prompt injection detected. Request rejected.",
                }
            ),
            400,
        )

    # 4. Cache lookup
    cache_key = make_cache_key("recommend", sanitized_text)
    cached = cache_get(cache_key)
    if cached:
        cached["cache_hit"] = True
        logger.info("Cache HIT for /recommend")
        return jsonify(cached), 200

    # 5. Get AI analysis first (internal describe call)
    describe_template = load_prompt("describe.txt")
    describe_prompt = describe_template.replace("{complaint}", sanitized_text)
    analysis_raw = call_groq(describe_prompt, temperature=0.3, max_tokens=1024)
    analysis_str = analysis_raw if analysis_raw else "Analysis unavailable."

    # 6. Query vector store for context enrichment
    context_docs = query_knowledge(sanitized_text, n_results=3)
    context_str = "\n".join(context_docs) if context_docs else ""

    # 7. Build recommend prompt — use .replace() NOT .format()
    template = load_prompt("recommend.txt")
    prompt = template.replace("{complaint}", sanitized_text).replace("{analysis}", analysis_str)
    if context_str:
        prompt += f"\n\nRelevant policy context:\n{context_str}"

    # 8. Call Groq
    raw = call_groq(prompt, temperature=0.3, max_tokens=1024)
    if raw is None:
        logger.warning("/recommend — Groq unavailable, returning fallback.")
        return jsonify(_fallback_recommendations()), 200

    # 9. Extract JSON (expecting a list)
    parsed = extract_json(raw)

    # 10. Validate structure
    valid = False
    if isinstance(parsed, list) and len(parsed) == 3:
        valid = all(
            isinstance(item, dict) and not validate_required_fields(item, _ITEM_FIELDS)
            for item in parsed
        )

    if not valid:
        logger.warning("/recommend — validation failed, returning fallback.")
        return jsonify(_fallback_recommendations()), 200

    # 11. Annotate items
    now = datetime.now(timezone.utc).isoformat()
    for item in parsed:
        item["generated_at"] = now
        item["is_fallback"] = False
        item["cache_hit"] = False

    response = {
        "recommendations": parsed,
        "generated_at": now,
        "is_fallback": False,
        "cache_hit": False,
    }

    # 12. Cache
    cache_set(cache_key, response)

    return jsonify(response), 200
from flask import Blueprint, request, jsonify, g

from services.groq_client import call_groq
from services.cache import cache_get, cache_set, make_cache_key
from routes.helpers import load_prompt, sanitise_input, extract_json, make_fallback

logger = logging.getLogger(__name__)

recommend_bp = Blueprint("recommend", __name__)

VALID_PRIORITIES = {"High", "Medium", "Low"}

# Fallback returned when the AI service is unavailable
FALLBACK_RESPONSE = {
    "recommendations": [
        {
            "action_type": "Investigation",
            "description": "Conduct an internal investigation into the reported matter.",
            "priority": "High",
        },
        {
            "action_type": "Documentation",
            "description": "Document all available evidence and witness statements.",
            "priority": "Medium",
        },
        {
            "action_type": "Policy Review",
            "description": "Review relevant policies to identify any gaps related to the report.",
            "priority": "Low",
        },
    ],
    "is_fallback": True,
}


def _validate_recommendations(data: dict) -> bool:
    """
    Return True if the parsed dict contains a valid 'recommendations' list
    with at least one item, each having the required fields.
    """
    recs = data.get("recommendations")
    if not isinstance(recs, list) or len(recs) == 0:
        return False
    for rec in recs:
        if not isinstance(rec, dict):
            return False
        if not rec.get("action_type") or not rec.get("description"):
            return False
        if rec.get("priority") not in VALID_PRIORITIES:
            # Normalise capitalisation before rejecting
            normalised = str(rec.get("priority", "")).capitalize()
            if normalised not in VALID_PRIORITIES:
                return False
            rec["priority"] = normalised
    return True


@recommend_bp.route("/recommend", methods=["POST"])
def recommend():
    # ── Validate request body ──────────────────────────────────────────────────
    body = request.get_json(silent=True)
    if not body:
        return jsonify({"error": "Request body must be valid JSON."}), 400

    raw_text = body.get("text", "")
    if not raw_text or not raw_text.strip():
        return jsonify({"error": "Field 'text' is required and must not be empty."}), 400

    if len(raw_text) > 5000:
        return jsonify({"error": "Field 'text' must not exceed 5000 characters."}), 400

    # ── Sanitise input (Fix #10: use middleware-cleaned value if available) ────
    if getattr(g, "sanitised", False):
        clean_text = g.clean_fields.get("text", raw_text.strip())
    else:
        try:
            clean_text = sanitise_input(raw_text)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

    # ── Check cache ─────────────────────────────────────────────────────────────
    cache_key = make_cache_key("recommend", clean_text)
    try:
        cached = cache_get(cache_key)
        if cached is not None:
            logger.info("Cache HIT for /recommend")
            result = {**cached, "generated_at": datetime.now(timezone.utc).isoformat()}
            return jsonify(result), 200
    except Exception as exc:
        logger.warning("Cache read failed for /recommend: %s", exc)

    # ── Build prompt ───────────────────────────────────────────────────────────
    generated_at = datetime.now(timezone.utc).isoformat()
    try:
        template = load_prompt("recommend_prompt.txt")
        # Use str.replace() for user-controlled field to avoid KeyError on curly braces.
        prompt = template.replace("{text}", clean_text)
    except Exception as exc:
        logger.error("Failed to load recommend prompt: %s", exc)
        return jsonify({"error": "Internal server error loading prompt."}), 500

    # ── Call Groq ──────────────────────────────────────────────────────────────
    try:
        raw_response = call_groq(prompt, temperature=0.3)
    except Exception as exc:
        logger.error("Groq call failed for /recommend: %s", exc)
        return jsonify(make_fallback(FALLBACK_RESPONSE, generated_at)), 200

    # ── Parse JSON ─────────────────────────────────────────────────────────────
    try:
        parsed = extract_json(raw_response)
    except ValueError as exc:
        logger.error("JSON parse failed for /recommend: %s | raw: %s", exc, raw_response[:300])
        return jsonify(make_fallback(FALLBACK_RESPONSE, generated_at)), 200

    # ── Validate structure ─────────────────────────────────────────────────────
    if not _validate_recommendations(parsed):
        logger.warning(
            "Groq /recommend response failed structure validation, using fallback. "
            "Parsed: %s", parsed
        )
        return jsonify(make_fallback(FALLBACK_RESPONSE, generated_at)), 200

    # I-1 FIX: Guarantee consistent envelope on all routes regardless of LLM output.
    parsed.setdefault("is_fallback", False)
    parsed.setdefault("generated_at", generated_at)

    # ── Cache successful (non-fallback) responses ──────────────────────────────
    if not parsed.get("is_fallback", False):
        try:
            cache_set(cache_key, parsed)
        except Exception as exc:
            logger.warning("Cache write failed for /recommend: %s", exc)

    return jsonify(parsed), 200
