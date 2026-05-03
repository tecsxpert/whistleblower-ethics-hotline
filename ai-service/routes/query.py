"""
POST /query — RAG-powered compliance knowledge base queries.
"""

import logging
import time

from flask import Blueprint, g, jsonify, request

from routes.helpers import extract_json, load_prompt
from services.groq_client import call_groq
from services.vector_store import similarity_search

logger = logging.getLogger(__name__)

query_bp = Blueprint("query", __name__)

_MAX_QUERY_LENGTH = 2000
_MAX_CONTEXT_CHUNK_CHARS = 1000

FALLBACK = {
    "answer": "The query service is temporarily unavailable.",
    "sources": [],
    "confidence": "Low",
    "generated_at": "",
    "is_fallback": True,
}


@query_bp.route("/query", methods=["POST"])
def query():
    """Answer a compliance question using RAG over the ethics knowledge base."""

    body = request.get_json(silent=True)
    if not body:
        return jsonify({"error": "Request body must be valid JSON."}), 400

    clean_fields = getattr(g, "clean_fields", {})
    clean_query = clean_fields.get("query", "")
    if not clean_query:
        raw_query = body.get("query", "")
        if not raw_query or not raw_query.strip():
            return jsonify({"error": "Field 'query' is required and must not be empty."}), 400
        clean_query = raw_query.strip()

    if len(clean_query) > _MAX_QUERY_LENGTH:
        return (
            jsonify(
                {
                    "error": f"Field 'query' exceeds maximum length of {_MAX_QUERY_LENGTH} characters."
                }
            ),
            400,
        )

    generated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # --- Similarity search ---
    sources: list[dict] = []
    try:
        results = similarity_search(clean_query, top_k=3)
    except Exception as exc:
        logger.error("VectorStore search failed: %s", exc)
        results = []

    # Build context block
    if results:
        context_parts: list[str] = []
        for idx, r in enumerate(results, start=1):
            chunk_text = r["text"][:_MAX_CONTEXT_CHUNK_CHARS]
            context_parts.append(
                f"[{idx}] Source: {r['source']} (relevance: {r['score']:.2f})\n{chunk_text}"
            )
            sources.append({"source": r["source"], "relevance": round(r["score"], 2)})
        context_block = "\n\n".join(context_parts)
    else:
        context_block = "No relevant documents found in the knowledge base."

    # Build source_list placeholder for prompt
    source_list_str = ", ".join(
        [f'{{"source": "{s["source"]}", "relevance": {s["relevance"]}}}' for s in sources]
    )

    try:
        template = load_prompt("query_prompt.txt")
        # Use str.replace() to avoid KeyError on curly braces in prompt
        prompt = (
            template.replace("{context}", context_block)
            .replace("{query}", clean_query)
            .replace("{source_list}", source_list_str)
            .replace("{generated_at}", generated_at)
        )
        raw_response = call_groq(prompt, temperature=0.3, max_tokens=1024)
        logger.info("Query response received (length=%d)", len(raw_response))

        parsed = extract_json(raw_response)

        # Overwrite sources with our authoritative list
        parsed["sources"] = sources

        # Normalise confidence
        confidence = parsed.get("confidence", "Low").strip().capitalize()
        if confidence not in ("High", "Medium", "Low"):
            confidence = "Low"
        parsed["confidence"] = confidence

        parsed.setdefault("generated_at", generated_at)
        parsed.setdefault("is_fallback", False)

        return jsonify(parsed), 200

    except Exception as exc:
        logger.error("Query endpoint error (query_length=%d): %s", len(clean_query), exc)
        fallback = dict(FALLBACK)
        fallback["generated_at"] = generated_at
        fallback["sources"] = sources  # preserve real sources
        return jsonify(fallback), 200
