"""
POST /generate-report — produce a formal investigation report.
"""

import json
import logging
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify

from middleware import sanitize_input
from helpers import extract_json, validate_required_fields
from services.groq_client import call_groq, load_prompt
from services.cache import make_cache_key, cache_get, cache_set
from services.vector_store import query_knowledge

logger = logging.getLogger(__name__)

report_bp = Blueprint("report", __name__, url_prefix="/generate-report")

_REQUIRED_FIELDS = [
    "title",
    "summary",
    "overview",
    "key_items",
    "recommendations",
    "risk_level",
    "estimated_resolution_days",
]


def _fallback_response() -> dict:
    """Return a deterministic fallback report when the AI is unavailable."""
    return {
        "title": "Ethics Investigation Report — Pending Review",
        "summary": "AI report generation is temporarily unavailable. A manual review is recommended.",
        "overview": (
            "The submitted complaint requires manual review by the ethics committee. "
            "An automated analysis could not be completed at this time. "
            "Please assign an investigator to assess the complaint details. "
            "Interim protective measures should be considered where applicable."
        ),
        "key_items": [
            "Complaint received and logged.",
            "Automated analysis unavailable.",
            "Manual review required.",
            "Interim measures may be needed.",
        ],
        "recommendations": [
            "Assign an impartial investigator.",
            "Preserve all relevant evidence.",
            "Schedule interviews with involved parties.",
        ],
        "risk_level": "Unknown",
        "estimated_resolution_days": 30,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "is_fallback": True,
        "cache_hit": False,
    }


@report_bp.route("/", methods=["POST"])
def generate_report():
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
    cache_key = make_cache_key("report", sanitized_text)
    cached = cache_get(cache_key)
    if cached:
        cached["cache_hit"] = True
        logger.info("Cache HIT for /generate-report")
        return jsonify(cached), 200

    # 5. Get AI analysis (internal describe call)
    describe_template = load_prompt("describe.txt")
    describe_prompt = describe_template.replace("{complaint}", sanitized_text)
    analysis_raw = call_groq(describe_prompt, temperature=0.3, max_tokens=1024)
    analysis_str = analysis_raw if analysis_raw else "Analysis unavailable."

    # 6. Get recommendations (internal recommend call)
    recommend_template = load_prompt("recommend.txt")
    recommend_prompt = recommend_template.replace(
        "{complaint}", sanitized_text
    ).replace("{analysis}", analysis_str)
    recs_raw = call_groq(recommend_prompt, temperature=0.3, max_tokens=1024)
    recs_str = recs_raw if recs_raw else "Recommendations unavailable."

    # 7. Query vector store for context enrichment
    context_docs = query_knowledge(sanitized_text, n_results=3)
    context_str = "\n".join(context_docs) if context_docs else ""

    # 8. Build report prompt
    template = load_prompt("report.txt")
    prompt = template.replace(
        "{complaint}", sanitized_text
    ).replace("{analysis}", analysis_str).replace("{recommendations}", recs_str)
    if context_str:
        prompt += f"\n\nRelevant policy context:\n{context_str}"

    # 9. Call Groq
    raw = call_groq(prompt, temperature=0.4, max_tokens=1500)
    if raw is None:
        logger.warning("/generate-report — Groq unavailable, returning fallback.")
        return jsonify(_fallback_response()), 200

    # 10. Extract JSON
    parsed = extract_json(raw)
    if parsed is None or not isinstance(parsed, dict):
        logger.warning("/generate-report — JSON extraction failed, returning fallback.")
        return jsonify(_fallback_response()), 200

    # 11. Validate required fields
    missing = validate_required_fields(parsed, _REQUIRED_FIELDS)
    if missing:
        logger.warning("/generate-report — Missing fields %s, returning fallback.", missing)
        return jsonify(_fallback_response()), 200

    # 12. Build response
    parsed["generated_at"] = datetime.now(timezone.utc).isoformat()
    parsed["is_fallback"] = False
    parsed["cache_hit"] = False

    # 13. Cache
    cache_set(cache_key, parsed)
POST /generate-report
Accepts { "text": "..." } and returns a structured formal compliance report.
"""

import logging
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify, g

from services.groq_client import call_groq
from services.cache import cache_get, cache_set, make_cache_key
from routes.helpers import load_prompt, sanitise_input, extract_json, make_fallback

logger = logging.getLogger(__name__)

report_bp = Blueprint("report", __name__)

FALLBACK_RESPONSE = {
    "title": "Compliance Report — AI Unavailable",
    "summary": "The AI report generation service is temporarily unavailable.",
    "overview": "Please review the original submission manually and generate a report.",
    "key_items": [],
    "recommendations": [],
    "generated_at": None,
    "is_fallback": True,
}


@report_bp.route("/generate-report", methods=["POST"])
def generate_report():
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
    cache_key = make_cache_key("generate-report", clean_text)
    try:
        cached = cache_get(cache_key)
        if cached is not None:
            logger.info("Cache HIT for /generate-report")
            result = {**cached, "generated_at": datetime.now(timezone.utc).isoformat()}
            return jsonify(result), 200
    except Exception as exc:
        logger.warning("Cache read failed for /generate-report: %s", exc)

    # ── Build prompt ───────────────────────────────────────────────────────────
    generated_at = datetime.now(timezone.utc).isoformat()
    try:
        template = load_prompt("report_prompt.txt")
        # Use str.replace() for user-controlled fields to avoid KeyError on curly braces.
        prompt = (
            template
            .replace("{text}", clean_text)
            .replace("{generated_at}", generated_at)
        )
    except Exception as exc:
        logger.error("Failed to load report prompt: %s", exc)
        return jsonify({"error": "Internal server error loading prompt."}), 500

    # ── Call Groq ──────────────────────────────────────────────────────────────
    try:
        raw_response = call_groq(prompt, temperature=0.4, max_tokens=1500)
    except Exception as exc:
        logger.error("Groq call failed for /generate-report: %s", exc)
        return jsonify(make_fallback(FALLBACK_RESPONSE, generated_at)), 200

    # ── Parse JSON ─────────────────────────────────────────────────────────────
    try:
        parsed = extract_json(raw_response)
    except ValueError as exc:
        logger.error(
            "JSON parse failed for /generate-report: %s | raw: %s", exc, raw_response[:300]
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
            logger.warning("Cache write failed for /generate-report: %s", exc)

    return jsonify(parsed), 200
