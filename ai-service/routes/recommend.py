"""
POST /recommend — AI-powered compliance recommendations.
"""

import logging
import time

from flask import Blueprint, g, jsonify, request

from routes.helpers import extract_json, load_prompt, truncate_for_prompt
from services.cache import cache_get, cache_set, make_cache_key
from services.groq_client import call_groq

logger = logging.getLogger(__name__)

recommend_bp = Blueprint("recommend", __name__)

VALID_PRIORITIES = {"High", "Medium", "Low"}

FALLBACK = {
    "recommendations": [
        {
            "action_type": "Investigation",
            "description": "Initiate a formal investigation into the reported incident.",
            "priority": "High",
        },
        {
            "action_type": "Documentation",
            "description": "Document all available evidence and witness statements.",
            "priority": "Medium",
        },
        {
            "action_type": "Policy Review",
            "description": "Review relevant organisational policies for compliance gaps.",
            "priority": "Low",
        },
    ],
    "is_fallback": True,
    "generated_at": "",
}


def _validate_recommendations(data: dict) -> bool:
    """Validate that recommendations meet structural requirements."""
    recs = data.get("recommendations")
    if not isinstance(recs, list) or len(recs) < 3:
        return False

    for rec in recs:
        if not isinstance(rec, dict):
            return False
        if "action_type" not in rec or "description" not in rec or "priority" not in rec:
            return False
        # Normalise capitalisation
        priority = rec["priority"].strip().capitalize()
        if priority not in VALID_PRIORITIES:
            return False
        rec["priority"] = priority

    return True


@recommend_bp.route("/recommend", methods=["POST"])
def recommend():
    """Generate compliance recommendations for a whistleblower report."""

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
    cache_key = make_cache_key("recommend", text)
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
        template = load_prompt("recommend_prompt.txt")
        prompt = template.replace("{text}", prompt_text)
        raw_response = call_groq(prompt, temperature=0.3)
        logger.info("Recommend response received (length=%d)", len(raw_response))

        parsed = extract_json(raw_response)

        if not _validate_recommendations(parsed):
            logger.warning(
                "Recommendation validation failed (count=%d)",
                len(parsed.get("recommendations", [])),
            )
            fallback = _make_fallback(generated_at)
            return jsonify(fallback), 200

        parsed.setdefault("is_fallback", False)
        parsed.setdefault("generated_at", generated_at)

        # Cache only valid, non-fallback results
        if not parsed.get("is_fallback"):
            cache_set(cache_key, parsed)

        return jsonify(parsed), 200

    except Exception as exc:
        logger.error("Recommend endpoint error (input_length=%d): %s", len(text), exc)
        fallback = _make_fallback(generated_at)
        return jsonify(fallback), 200


def _make_fallback(generated_at: str) -> dict:
    """Return a deep copy of the fallback with ``generated_at`` set."""
    import copy

    fb = copy.deepcopy(FALLBACK)
    fb["generated_at"] = generated_at
    return fb
