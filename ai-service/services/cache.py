"""
Redis caching layer — SHA-256 keyed, fail-silent on connection errors.
"""

import os
import json
import hashlib
import logging
from typing import Optional

import redis

logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────────
REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379")
DEFAULT_TTL: int = 900  # 15 minutes

# ── Singleton client with lazy initialisation ────────────────────────
_redis_client: Optional[redis.Redis] = None
_CONNECT_TIMEOUT: int = 30  # seconds


def _get_redis() -> Optional[redis.Redis]:
    """Return the Redis client, creating it lazily.  Never raises."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        _redis_client = redis.Redis.from_url(
            REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=_CONNECT_TIMEOUT,
            socket_timeout=5,
        )
        _redis_client.ping()
        logger.info("Redis connected at %s", REDIS_URL)
    except Exception as exc:
        logger.warning("Redis unavailable — caching disabled: %s", exc)
        _redis_client = None
    return _redis_client


def make_cache_key(endpoint: str, text: str) -> str:
    """SHA-256 hex digest of ``endpoint:text``."""
    raw = f"{endpoint}:{text}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def cache_get(key: str) -> Optional[dict]:
    """Retrieve cached value.  Returns ``None`` on miss or error."""
    try:
        client = _get_redis()
        if client is None:
            return None
        data = client.get(key)
        if data is None:
            return None
        return json.loads(data)
    except Exception as exc:
        logger.warning("cache_get failed (key=%s): %s", key[:16], exc)
        return None


def cache_set(key: str, value: dict, ttl: int = DEFAULT_TTL) -> None:
    """Store a value in the cache.  Fails silently."""
    try:
        client = _get_redis()
        if client is None:
            return
        client.setex(key, ttl, json.dumps(value))
    except Exception as exc:
        logger.warning("cache_set failed (key=%s): %s", key[:16], exc)


def is_redis_connected() -> bool:
    """Return ``True`` if Redis is reachable right now."""
    try:
        client = _get_redis()
        if client is None:
            return False
        client.ping()
        return True
    except Exception:
        return False
