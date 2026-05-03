"""
Redis caching layer with resilient connection management.
Silently degrades to no-op when Redis is unavailable.
"""

import hashlib
import json
import logging
import time

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------
_redis_client = None
_redis_warned = False
_next_retry_time: float = 0.0


def _get_redis():
    """Return a live Redis client or ``None`` if unavailable."""
    global _redis_client, _redis_warned, _next_retry_time
    import os

    if _redis_client is not None:
        return _redis_client

    if time.time() < _next_retry_time:
        return None

    redis_url = os.getenv("REDIS_URL", "")
    if not redis_url:
        if not _redis_warned:
            logger.warning("REDIS_URL not set — caching disabled.")
            _redis_warned = True
        return None

    try:
        import redis

        client = redis.from_url(redis_url, socket_connect_timeout=2)
        client.ping()
        _redis_client = client
        logger.info("Redis connected: %s", redis_url)
        return _redis_client
    except Exception as exc:
        _next_retry_time = time.time() + 30
        if not _redis_warned:
            logger.warning("Redis unavailable (retry in 30 s): %s", exc)
            _redis_warned = True
        return None


def make_cache_key(endpoint: str, text: str) -> str:
    """SHA-256 hex digest of ``endpoint:text`` — always 64 characters."""
    return hashlib.sha256(f"{endpoint}:{text}".encode()).hexdigest()


def cache_get(key: str) -> dict | None:
    """Retrieve a cached value. Returns ``None`` on miss or error."""
    global _redis_client, _redis_warned

    r = _get_redis()
    if r is None:
        return None

    try:
        raw = r.get(key)
        if raw is None:
            logger.debug("Cache MISS: %s", key[:16])
            return None
        logger.debug("Cache HIT: %s", key[:16])
        return json.loads(raw)
    except Exception as exc:
        logger.warning("Redis GET error (resetting client): %s", exc)
        _redis_client = None
        _redis_warned = False
        return None


def cache_set(key: str, value: dict, ttl_seconds: int = 900) -> None:
    """Store a value in cache with TTL. No-op on error."""
    global _redis_client, _redis_warned

    r = _get_redis()
    if r is None:
        return

    try:
        r.setex(key, ttl_seconds, json.dumps(value))
    except Exception as exc:
        logger.warning("Redis SETEX error (resetting client): %s", exc)
        _redis_client = None
        _redis_warned = False
