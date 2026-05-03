"""
POST /generate-report — AI-powered compliance report generation.
"""

import copy
import logging
import time

from flask import Blueprint, g, jsonify, request

from routes.helpers import extract_json, load_prompt, truncate_for_prompt
from services.cache import cache_get, cache_set, make_cache_key
from services.groq_client import call_groq

logger = logging.getLogger(__name__)

report_bp = Blueprint("report", __name__)

REQUIRED_REPORT_FIELDS = ["title", "summary", "overview", "key_items", "recommendations"]

FALLBACK = {
    "title": "Compliance Report — AI Unavailable",
    "summary": "AI report generation is temporarily unavailable.",
    "overview": "Please review the original submission manually.",
    "key_items": [],
    "recommendations": [],
    "generated_at": "",
    "is_fallback": True,
}


def _validate_report(data: dict) -> bool:
    """Validate that the report contains all required, non-empty fields."""
    for field in REQUIRED_REPORT_FIELDS:
        if not data.get(field):
            return False
    if not isinstance(data.get("key_items"), list) or len(data["key_items"]) == 0:
        return False
    if not isinstance(data.get("recommendations"), list) or len(data["recommendations"]) == 0:
        return False
    return True


@report_bp.route("/generate-report", methods=["POST"])
def generate_report():
    """Generate a formal compliance report from a whistleblower submission."""

    body = request.get_json(silent=True)
    if not body:
        return jsonify({"error": "Request body must be valid JSON."}), 400

    clean_fields = getattr(g, "clean_fields", {})
    text = clean_fields.get("text", "")
    if not text:
        raw_text = body.get("text", "")
        if not raw_text or not raw_text.strip():
            return jsonify({"error": "Field 'text' is required and must not be empty."}), 400
        text = raw_text.strip()

    if len(text) > 5000:
        return jsonify({"error": "Field 'text' exceeds maximum length of 5000 characters."}), 400

    generated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # Cache check
    cache_key = make_cache_key("generate-report", text)
    try:
        cached = cache_get(cache_key)
        if cached is not None:
            cached["generated_at"] = generated_at
            return jsonify(cached), 200
    except Exception as cache_exc:
        logger.warning("Cache read failed (non-fatal): %s", cache_exc)

    # Truncate for prompt safety
    prompt_text = truncate_for_prompt(text)

    try:
        template = load_prompt("report_prompt.txt")
        prompt = template.replace("{text}", prompt_text).replace(
            "{generated_at}", generated_at
        )
        raw_response = call_groq(prompt, temperature=0.4, max_tokens=1500)
        logger.info("Report response received (length=%d)", len(raw_response))

        parsed = extract_json(raw_response)

        if not _validate_report(parsed):
            logger.warning("Report validation failed — returning fallback.")
            fallback = copy.deepcopy(FALLBACK)
            fallback["generated_at"] = generated_at
            return jsonify(fallback), 200

        parsed.setdefault("is_fallback", False)
        parsed.setdefault("generated_at", generated_at)

        # Cache only valid, non-fallback results
        if not parsed.get("is_fallback"):
            cache_set(cache_key, parsed)

        return jsonify(parsed), 200

    except Exception as exc:
        logger.error("Report endpoint error (input_length=%d): %s", len(text), exc)
        fallback = copy.deepcopy(FALLBACK)
        fallback["generated_at"] = generated_at
        return jsonify(fallback), 200
