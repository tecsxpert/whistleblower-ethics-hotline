"""
POST /describe — classify and summarise a whistleblower complaint.
"""

import json
import logging
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify
POST /describe
Accepts { "text": "..." } and returns a structured AI description of the report.
"""

import logging
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify, g

from services.groq_client import call_groq
from services.cache import cache_get, cache_set, make_cache_key
from routes.helpers import load_prompt, sanitise_input, extract_json, make_fallback

logger = logging.getLogger(__name__)

from middleware import sanitize_input
from helpers import extract_json, validate_required_fields
from services.groq_client import call_groq, load_prompt
from services.cache import make_cache_key, cache_get, cache_set
from services.vector_store import query_knowledge
from services.metrics import track

logger = logging.getLogger(__name__)

describe_bp = Blueprint("describe", __name__, url_prefix="/describe")

_REQUIRED_FIELDS = [
    "category",
    "severity",
    "summary",
    "key_facts",
    "recommended_action",
    "confidence_score",
]

# ── Rule-based category classifier (fallback when AI returns "Other") ─
_CATEGORY_RULES: list[tuple[list[str], str]] = [
    (["fraud", "embezzlement", "invoice", "financial"], "Financial Fraud"),
    (["harassment", "bully", "hostile"], "Harassment"),
    (["leak", "data", "breach", "pii"], "Data Leak"),
    (["ethics", "conflict of interest", "bribery", "corruption"], "Ethics Violation"),
]


def _classify_category(text: str, ai_category: str) -> str:
    """
    If the AI returned a vague category ('Other' or empty), apply
    rule-based classification against the original complaint text.
    """
    if ai_category and ai_category.lower() not in ("other", ""):
        return ai_category

    lower = text.lower()
    for keywords, label in _CATEGORY_RULES:
        if any(kw in lower for kw in keywords):
            return label

    return "General Misconduct"


def _fallback_response() -> dict:
    """Return a deterministic fallback when the AI is unavailable."""
    return {
        "category": "Unable to determine",
        "severity": "Unknown",
        "summary": "AI analysis temporarily unavailable.",
        "key_facts": [],
        "recommended_action": "Please review manually.",
        "confidence_score": 0.0,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "is_fallback": True,
        "cache_hit": False,
    }


@describe_bp.route("/", methods=["POST"])
@track("/describe")
def describe():
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
    cache_key = make_cache_key("describe", sanitized_text)
    cached = cache_get(cache_key)
    if cached:
        cached["cache_hit"] = True
        logger.info("Cache HIT for /describe")
        return jsonify(cached), 200

    # 5. Query vector store for context enrichment
    context_docs = query_knowledge(sanitized_text, n_results=3)
    context_str = "\n".join(context_docs) if context_docs else ""

    # 6. Build prompt
    template = load_prompt("describe.txt")
    prompt = template.replace("{complaint}", sanitized_text)
    if context_str:
        prompt += f"\n\nRelevant policy context:\n{context_str}"

    # 7. Call Groq
    raw = call_groq(prompt, temperature=0.3, max_tokens=1024)
    if raw is None:
        logger.warning("/describe — Groq unavailable, returning fallback.")
        return jsonify(_fallback_response()), 200

    # 8. Extract JSON
    parsed = extract_json(raw)
    if parsed is None or not isinstance(parsed, dict):
        logger.warning("/describe — JSON extraction failed, returning fallback.")
        return jsonify(_fallback_response()), 200

    # 9. Validate required fields
    missing = validate_required_fields(parsed, _REQUIRED_FIELDS)
    if missing:
        logger.warning("/describe — Missing fields %s, returning fallback.", missing)
        return jsonify(_fallback_response()), 200

    # 10. Apply category fallback classifier
    parsed["category"] = _classify_category(sanitized_text, parsed.get("category", ""))

    # 11. Build response
    parsed["generated_at"] = datetime.now(timezone.utc).isoformat()
    parsed["cache_hit"] = False
    parsed["is_fallback"] = False

    # 12. Cache
    cache_set(cache_key, parsed)
# Fallback returned when the AI service is unavailable
FALLBACK_RESPONSE = {
    "category": "Unknown",
    "severity": "Unknown",
    "summary": "AI description is temporarily unavailable.",
    "key_entities": [],
    "recommended_action": "Please review the report manually.",
    "generated_at": None,
    "is_fallback": True,
}


@describe_bp.route("/describe", methods=["POST"])
def describe():
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
    cache_key = make_cache_key("describe", clean_text)
    try:
        cached = cache_get(cache_key)
        if cached is not None:
            logger.info("Cache HIT for /describe")
            # ME-14 FIX: Explicit copy — don't mutate the dict returned by cache_get.
            result = {**cached, "generated_at": datetime.now(timezone.utc).isoformat()}
            return jsonify(result), 200
    except Exception as exc:
        logger.warning("Cache read failed for /describe: %s", exc)

    # ── Build prompt ───────────────────────────────────────────────────────────
    generated_at = datetime.now(timezone.utc).isoformat()
    try:
        template = load_prompt("describe_prompt.txt")
        # Use str.replace() for user-controlled field to avoid KeyError on curly braces.
        prompt = (
            template
            .replace("{text}", clean_text)
            .replace("{generated_at}", generated_at)
        )
    except Exception as exc:
        logger.error("Failed to load describe prompt: %s", exc)
        return jsonify({"error": "Internal server error loading prompt."}), 500

    # ── Call Groq ──────────────────────────────────────────────────────────────
    try:
        raw_response = call_groq(prompt, temperature=0.3)
    except Exception as exc:
        logger.error("Groq call failed for /describe: %s", exc)
        return jsonify(make_fallback(FALLBACK_RESPONSE, generated_at)), 200

    # ── Parse JSON ─────────────────────────────────────────────────────────────
    try:
        parsed = extract_json(raw_response)
    except ValueError as exc:
        logger.error("JSON parse failed for /describe: %s | raw: %s", exc, raw_response[:300])
        return jsonify(make_fallback(FALLBACK_RESPONSE, generated_at)), 200

    # I-1 FIX: Guarantee consistent envelope on all routes regardless of LLM output.
    parsed.setdefault("is_fallback", False)
    parsed.setdefault("generated_at", generated_at)

    # ── Cache successful (non-fallback) responses ──────────────────────────────
    if not parsed.get("is_fallback", False):
        try:
            cache_set(cache_key, parsed)
        except Exception as exc:
            logger.warning("Cache write failed for /describe: %s", exc)

    return jsonify(parsed), 200
