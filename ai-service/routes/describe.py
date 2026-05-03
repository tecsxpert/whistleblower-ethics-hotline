"""
POST /describe — AI-powered report classification and summarisation.
"""

import logging
import time

from flask import Blueprint, g, jsonify, request

from routes.helpers import extract_json, load_prompt, truncate_for_prompt
from services.cache import cache_get, cache_set, make_cache_key
from services.groq_client import call_groq

logger = logging.getLogger(__name__)

describe_bp = Blueprint("describe", __name__)

FALLBACK = {
    "category": "Unknown",
    "severity": "Unknown",
    "summary": "AI description is temporarily unavailable.",
    "key_entities": [],
    "recommended_action": "Please review the report manually.",
    "generated_at": "",
    "is_fallback": True,
}


@describe_bp.route("/describe", methods=["POST"])
def describe():
    """Classify and summarise a whistleblower report."""

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
    cache_key = make_cache_key("describe", text)
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
        template = load_prompt("describe_prompt.txt")
        prompt = template.replace("{text}", prompt_text).replace(
            "{generated_at}", generated_at
        )
        raw_response = call_groq(prompt, temperature=0.3)
        logger.info("Describe response received (length=%d)", len(raw_response))

        parsed = extract_json(raw_response)
        parsed.setdefault("is_fallback", False)
        parsed.setdefault("generated_at", generated_at)

        # Cache successful (non-fallback) results
        if not parsed.get("is_fallback"):
            cache_set(cache_key, parsed)

        return jsonify(parsed), 200

    except Exception as exc:
        logger.error("Describe endpoint error (input_length=%d): %s", len(text), exc)
        fallback = dict(FALLBACK)
        fallback["generated_at"] = generated_at
        return jsonify(fallback), 200
