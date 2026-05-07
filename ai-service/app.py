"""
Tool-70 — Whistleblower & Ethics Hotline AI Microservice
Flask application factory with production-grade security hardening.
"""

import os
import time
import logging
from datetime import datetime, timezone
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

    # ── Production config ────────────────────────────────────────────
    # Limit request body size to 16 KB — prevents memory exhaustion
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024  # 16 KB

    # Disable debug in production (read from env var for flexibility)
    app.config["DEBUG"] = os.getenv("FLASK_DEBUG", "false").lower() == "true"

    # Disable default exception propagation to prevent stack trace leakage
    app.config["PROPAGATE_EXCEPTIONS"] = False

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
        # Prevent MIME-type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Strict CSP — this is a pure API, no resources needed
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; frame-ancestors 'none'"
        )

        # Enforce HTTPS for 1 year
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )

        # Prevent caching of sensitive AI responses
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
        response.headers["Pragma"] = "no-cache"

        # Disable browser feature access
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), payment=()"
        )

        # Referrer policy
        response.headers["Referrer-Policy"] = "no-referrer"

        # Remove server fingerprinting headers
        response.headers.pop("Server", None)
        response.headers.pop("X-Powered-By", None)

        return response

    # ── Global error handlers (JSON, no stack trace leakage) ─────────
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({"error": "Bad request", "status": 400}), 400

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Endpoint not found", "status": 404}), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({"error": "Method not allowed", "status": 405}), 405

    @app.errorhandler(413)
    def payload_too_large(error):
        return (
            jsonify(
                {
                    "error": "Request body too large. Maximum size is 16 KB.",
                    "status": 413,
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
    def rate_limit_exceeded(error):
        return (
            jsonify(
                {
                    "error": "Rate limit exceeded. Maximum 30 requests per minute.",
                    "status": 429,
                }
            ),
            429,
        )

    @app.errorhandler(500)
    def internal_error(error):
        logger.error("Internal server error: %s", error, exc_info=True)
        return (
            jsonify(
                {
                    "error": "AI service temporarily unavailable. Please try again.",
                    "is_fallback": True,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "status": 500,
                }
            ),
            500,
        )

    @app.errorhandler(Exception)
    def unhandled_exception(error):
        logger.error("Unhandled exception: %s", error, exc_info=True)
        return (
            jsonify(
                {
                    "error": "AI service temporarily unavailable. Please try again.",
                    "is_fallback": True,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
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
