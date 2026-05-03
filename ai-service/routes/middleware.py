"""
Request-level middleware: request-ID assignment, content-type validation,
JSON body parsing, field sanitisation.
"""

import logging
import uuid

from flask import g, jsonify, request

from routes.helpers import sanitise_input

logger = logging.getLogger(__name__)

# Endpoints that expect a JSON body with text/query fields
_TEXT_ENDPOINTS = {"/describe", "/recommend", "/generate-report", "/query"}


def sanitise_middleware():
    """Pre-process incoming requests.

    Registered as a ``before_request`` handler in ``app.py``.
    Returns ``None`` to let the request continue, or a ``(response, status)``
    tuple to short-circuit.
    """
    # Assign a request ID
    g.request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

    # Only validate POST requests to text endpoints
    if request.method != "POST" or request.path not in _TEXT_ENDPOINTS:
        return None

    # Content-Type must be JSON
    content_type = request.content_type or ""
    if "application/json" not in content_type:
        return jsonify({"error": "Content-Type must be application/json."}), 415

    # Parse JSON body
    body = request.get_json(silent=True)
    if body is None:
        return jsonify({"error": "Request body must be valid JSON."}), 400

    # JSON bomb protection
    if len(body) > 20:
        return jsonify({"error": "Request body has too many fields."}), 400

    # Sanitise known text fields
    g.clean_fields = {}
    for field in ("text", "query"):
        value = body.get(field)
        if value is None:
            continue
        if not isinstance(value, str):
            continue
        try:
            cleaned = sanitise_input(value)
            g.clean_fields[field] = cleaned
        except ValueError:
            return (
                jsonify(
                    {
                        "error": f"Input rejected: potentially unsafe content in '{field}'."
                    }
                ),
                400,
            )

    g.sanitised = True
    return None
