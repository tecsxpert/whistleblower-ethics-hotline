"""
Tool-70 — Whistleblower & Ethics Hotline AI Microservice
Flask application factory with security hardening.
"""

import os
import time
import logging
from flask import Flask, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# ── App start time (used by /health for uptime) ──────────────────────
app_start_time = time.time()

# ── Logging ──────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


def create_app() -> Flask:
    """Application factory — creates and configures the Flask app."""

    app = Flask(__name__)

    # ── Payload size protection: 1 MB max ────────────────────────────
    app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024

    # ── Rate limiter: 30 requests / minute per IP ────────────────────
    # Uses memory:// so tests pass without a running Redis instance.
    limiter = Limiter(
        key_func=get_remote_address,
        app=app,
        default_limits=["30 per minute"],
        storage_uri="memory://",
    )

    # ── Register blueprints ──────────────────────────────────────────
    from routes.describe import describe_bp
    from routes.recommend import recommend_bp
    from routes.report import report_bp
    from routes.health import health_bp

    app.register_blueprint(describe_bp)
    app.register_blueprint(recommend_bp)
    app.register_blueprint(report_bp)
    app.register_blueprint(health_bp)

    # ── Security headers (every response) ────────────────────────────
    @app.after_request
    def add_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = "default-src 'none'"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Permissions-Policy"] = "geolocation=()"
        response.headers["Strict-Transport-Security"] = "max-age=31536000"
        return response

    # ── Global error handlers (JSON) ─────────────────────────────────
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({"error": "Bad request", "message": str(error)}), 400

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Not found", "message": str(error)}), 404

    @app.errorhandler(413)
    def payload_too_large(error):
        return (
            jsonify(
                {
                    "error": "Payload too large",
                    "message": "Request body must not exceed 1 MB.",
                }
            ),
            413,
        )

    @app.errorhandler(415)
    def unsupported_media(error):
        return (
            jsonify(
                {
                    "error": "Unsupported media type",
                    "message": "Content-Type must be application/json",
                }
            ),
            415,
        )

    @app.errorhandler(429)
    def rate_limited(error):
        return (
            jsonify(
                {
                    "error": "Rate limit exceeded",
                    "message": "Maximum 30 requests per minute. Please retry later.",
                }
            ),
            429,
        )

    @app.errorhandler(500)
    def internal_error(error):
        logger.exception("Internal server error")
        return (
            jsonify(
                {
                    "error": "Internal server error",
                    "message": "An unexpected error occurred.",
                }
            ),
            500,
        )

    logger.info("Tool-70 AI Microservice initialised successfully.")
    return app


# ── Module-level app instance for gunicorn (`app:app`) ───────────────
app = create_app()

# ── Entry point (local development) ─────────────────────────────────
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
