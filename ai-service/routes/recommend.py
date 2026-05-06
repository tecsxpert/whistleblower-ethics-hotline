"""
POST /recommend — generate investigation recommendations for a complaint.
"""

import logging
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify

from middleware import sanitize_input
from helpers import extract_json, validate_required_fields
from services.groq_client import call_groq, load_prompt
from services.cache import make_cache_key, cache_get, cache_set
from services.vector_store import query_knowledge

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
