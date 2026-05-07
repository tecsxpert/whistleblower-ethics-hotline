"""
GET /health — service health check with uptime, connectivity, and metrics.
"""

import logging
import time

from flask import Blueprint, jsonify

from services.groq_client import MODEL_NAME
from services.metrics import metrics
from services.cache import is_redis_connected, DEFAULT_TTL
from services.vector_store import is_chromadb_connected

logger = logging.getLogger(__name__)

health_bp = Blueprint("health", __name__, url_prefix="/health")


@health_bp.route("/", methods=["GET"])
def health():
    # Import app_start_time inside the function to avoid circular import
    from app import app_start_time

    uptime = time.time() - app_start_time

    # Get per-endpoint metrics from the new MetricsCollector
    all_stats = metrics.get_all_stats()

    try:
        redis_ok = is_redis_connected()
    except Exception:
        redis_ok = False

    try:
        chroma_ok = is_chromadb_connected()
    except Exception:
        chroma_ok = False

    status = "healthy" if (redis_ok and chroma_ok) else "degraded"

    payload = {
        "status": status,
        "model": MODEL_NAME,
        "uptime_seconds": round(uptime, 2),
        "endpoints": all_stats.get("endpoints", {}),
        "redis_connected": redis_ok,
        "chromadb_connected": chroma_ok,
        "available_endpoints": ["/describe", "/recommend", "/generate-report", "/health"],
        "rate_limit": "30 per minute",
        "cache_ttl_seconds": DEFAULT_TTL,
    }

    return jsonify(payload), 200
