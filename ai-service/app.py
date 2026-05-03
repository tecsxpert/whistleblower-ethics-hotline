"""
Whistleblower & Ethics Hotline — AI Microservice
Flask application factory with production-ready configuration.
"""

import collections
import logging
import os
import threading
import time
from collections import defaultdict, deque
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, g, jsonify, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
load_dotenv(Path(__file__).resolve().parent / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level timing lock (shared across requests)
# ---------------------------------------------------------------------------
_times_lock = threading.Lock()

# ---------------------------------------------------------------------------
# Application start timestamp (set BEFORE heavy imports)
# ---------------------------------------------------------------------------
START_TIME = time.time()


def create_app() -> Flask:
    """Application factory — creates and configures the Flask app."""

    app = Flask(__name__)

    # ---- Groq API key validation ----
    skip_validation = os.getenv("SKIP_GROQ_VALIDATION", "false").lower() == "true"
    groq_key = os.getenv("GROQ_API_KEY", "")
    if not skip_validation:
        if not groq_key or groq_key in (
            "your_groq_api_key_here",
            "changeme",
            "placeholder",
        ):
            raise RuntimeError(
                "GROQ_API_KEY is missing or contains a placeholder value. "
                "Set a valid key in .env or pass SKIP_GROQ_VALIDATION=true."
            )
    logger.info("GROQ_API_KEY loaded successfully (length=%d)", len(groq_key))

    # ---- Max content length ----
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024

    # ---- Response-time tracking structures ----
    app.config["RESPONSE_TIMES"] = collections.deque(maxlen=100)
    app.config["ENDPOINT_TIMES"] = defaultdict(lambda: deque(maxlen=50))

    # ---- Rate limiter ----
    redis_url = os.getenv("REDIS_URL", "")
    if redis_url:
        storage_uri = redis_url
        logger.info("Rate-limiter using Redis backend: %s", redis_url)
    else:
        storage_uri = "memory://"
        logger.warning(
            "REDIS_URL not set — rate-limiter falling back to in-memory storage."
        )

    limiter = Limiter(
        key_func=get_remote_address,
        app=app,
        default_limits=["30 per minute"],
        storage_uri=storage_uri,
    )  # noqa: F841 — limiter attaches itself to the app

    # ---- CORS ----
    allowed = os.getenv(
        "ALLOWED_ORIGINS", "http://localhost:8080,http://127.0.0.1:8080"
    )
    origins = [o.strip() for o in allowed.split(",") if o.strip()]
    CORS(app, origins=origins)

    # ---- Register blueprints ----
    from routes.describe import describe_bp
    from routes.query import query_bp
    from routes.recommend import recommend_bp
    from routes.report import report_bp

    app.register_blueprint(describe_bp)
    app.register_blueprint(recommend_bp)
    app.register_blueprint(report_bp)
    app.register_blueprint(query_bp)

    # ---- Middleware ----
    from routes.middleware import sanitise_middleware

    app.before_request(sanitise_middleware)

    # ---- Before-request: timing start + request-id ----
    @app.before_request
    def _start_timer():
        g.start_time = time.time()

    # ---- After-request: security headers + timing ----
    @app.after_request
    def _security_and_timing(response):
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; frame-ancestors 'none'"
        )
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=()"
        )
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        # Remove server header
        response.headers.pop("Server", None)

        # X-Request-ID
        request_id = getattr(g, "request_id", None)
        if request_id:
            response.headers["X-Request-ID"] = request_id

        # Timing
        start = getattr(g, "start_time", None)
        if start is not None:
            elapsed = (time.time() - start) * 1000  # ms
            with _times_lock:
                app.config["RESPONSE_TIMES"].append(elapsed)
                endpoint_key = request.endpoint or request.path
                app.config["ENDPOINT_TIMES"][endpoint_key].append(elapsed)

        return response

    # ---- VectorStore pre-load ----
    try:
        from services.vector_store import initialise as vs_init

        vs_init()
        logger.info("VectorStore initialised successfully.")
    except Exception as exc:
        logger.error("VectorStore init failed (non-fatal): %s", exc)

    # ---- Health endpoint ----
    @app.route("/health", methods=["GET"])
    def health():
        from services.vector_store import document_count

        uptime = time.time() - START_TIME

        with _times_lock:
            times_snapshot = list(app.config["RESPONSE_TIMES"])
            endpoint_snapshot = {
                k: list(v) for k, v in app.config["ENDPOINT_TIMES"].items()
            }

        avg_ms = (
            round(sum(times_snapshot) / len(times_snapshot), 2)
            if times_snapshot
            else 0.0
        )

        endpoint_avg_ms = {}
        for ep, vals in endpoint_snapshot.items():
            if vals:
                endpoint_avg_ms[ep] = round(sum(vals) / len(vals), 2)

        slow_endpoints = [k for k, v in endpoint_avg_ms.items() if v > 2000]

        try:
            doc_count = document_count()
        except Exception:
            doc_count = -1

        return jsonify(
            {
                "status": "ok",
                "model": "llama-3.3-70b-versatile",
                "embedding_model": "all-MiniLM-L6-v2",
                "vector_store_documents": doc_count,
                "uptime_seconds": round(uptime, 2),
                "avg_response_ms": avg_ms,
                "endpoint_avg_ms": endpoint_avg_ms,
                "slow_endpoints": slow_endpoints,
                "performance_target_ms": 2000,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
        ), 200

    # ---- Ping ----
    @app.route("/ping", methods=["GET"])
    def ping():
        return jsonify({"pong": True}), 200

    # ---- Error handlers ----
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Not found", "status": 404}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"error": "Method not allowed", "status": 405}), 405

    @app.errorhandler(429)
    def rate_limited(e):
        return (
            jsonify(
                {
                    "error": "Rate limit exceeded. Please try again later.",
                    "status": 429,
                }
            ),
            429,
        )

    @app.errorhandler(413)
    def payload_too_large(e):
        return (
            jsonify({"error": "Request payload too large.", "status": 413}),
            413,
        )

    @app.errorhandler(500)
    def internal_error(e):
        logger.error("Internal server error: %s", e)
        return (
            jsonify({"error": "Internal server error.", "status": 500}),
            500,
        )

    return app


# ---------------------------------------------------------------------------
# Module-level app instance for Gunicorn (gunicorn app:app)
# ---------------------------------------------------------------------------
app = create_app()

if __name__ == "__main__":
    logger.warning(
        "Running with the built-in Flask server — FOR DEVELOPMENT ONLY. "
        "Use Gunicorn in production."
    )
    port = int(os.getenv("AI_PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
