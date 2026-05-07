"""
ai-service/services/metrics.py
================================
Thread-Safe Metrics Collector — Tool-70 Whistleblower & Ethics Hotline

Tracks per-endpoint response times and request counts.
Used by GET /health to report avg response time and uptime.

Design:
- Uses collections.deque (bounded, thread-safe for append/popleft)
- Uses threading.Lock for aggregate computations
- No external dependencies

Backward Compatibility:
- ``last_100_response_times`` and ``metrics_lock`` are still exported
  so that ``groq_client.py`` continues to work without changes.

Usage (in routes):
    from services.metrics import track

    @app.route("/describe", methods=["POST"])
    @track("/describe")
    def describe():
        ...

    # Read stats (from /health endpoint)
    from services.metrics import metrics
    all_stats = metrics.get_all_stats()
"""

import threading
import time
from collections import defaultdict, deque
from typing import Optional

# Maximum number of recent requests to keep per endpoint
# (bounded deque prevents unbounded memory growth)
_WINDOW_SIZE = 200


class _EndpointMetrics:
    """Metrics for a single endpoint."""

    def __init__(self):
        # deque.append() is thread-safe in CPython due to the GIL,
        # but we use a Lock for the aggregate read operations to be safe
        # on non-CPython interpreters and for compound operations.
        self._lock = threading.Lock()
        self._times: deque = deque(maxlen=_WINDOW_SIZE)   # elapsed seconds
        self._successes: deque = deque(maxlen=_WINDOW_SIZE)  # bool
        self._total_count = 0

    def record(self, elapsed_seconds: float, success: bool = True):
        with self._lock:
            self._times.append(elapsed_seconds)
            self._successes.append(success)
            self._total_count += 1

    def get_stats(self) -> dict:
        with self._lock:
            times = list(self._times)
            successes = list(self._successes)
            total = self._total_count

        if not times:
            return {
                "total_requests": total,
                "window_size": 0,
                "avg_ms": None,
                "min_ms": None,
                "max_ms": None,
                "success_rate": None,
                "slow_requests": 0,
            }

        avg_ms = (sum(times) / len(times)) * 1000
        min_ms = min(times) * 1000
        max_ms = max(times) * 1000
        success_rate = sum(successes) / len(successes) if successes else 0
        slow = sum(1 for t in times if t > 2.0)

        return {
            "total_requests": total,
            "window_size": len(times),
            "avg_ms": round(avg_ms, 1),
            "min_ms": round(min_ms, 1),
            "max_ms": round(max_ms, 1),
            "success_rate": round(success_rate, 4),
            "slow_requests": slow,
        }


class MetricsCollector:
    """
    Application-wide metrics collector.
    Thread-safe. Singleton — import and use `metrics` directly.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._endpoints: dict[str, _EndpointMetrics] = defaultdict(_EndpointMetrics)
        self._start_time = time.time()

    def record(self, endpoint: str, elapsed_seconds: float, success: bool = True):
        """Record a completed request."""
        with self._lock:
            em = self._endpoints[endpoint]
        em.record(elapsed_seconds, success)

    def get_stats(self, endpoint: str) -> dict:
        """Get stats for a specific endpoint."""
        with self._lock:
            em = self._endpoints.get(endpoint)
        if em is None:
            return {"total_requests": 0, "window_size": 0}
        return em.get_stats()

    def get_all_stats(self) -> dict:
        """Get stats for all endpoints — used by /health."""
        with self._lock:
            endpoint_names = list(self._endpoints.keys())

        endpoint_stats = {}
        for name in endpoint_names:
            endpoint_stats[name] = self.get_stats(name)

        uptime_seconds = int(time.time() - self._start_time)

        return {
            "uptime_seconds": uptime_seconds,
            "endpoints": endpoint_stats,
        }

    def get_uptime_seconds(self) -> int:
        return int(time.time() - self._start_time)


# ---------------------------------------------------------------------------
# Singleton instance — import this in routes and app.py
# ---------------------------------------------------------------------------
metrics = MetricsCollector()


# ---------------------------------------------------------------------------
# Backward compatibility — groq_client.py imports these directly
# ---------------------------------------------------------------------------
last_100_response_times: deque = deque(maxlen=100)
metrics_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Convenience decorator for automatic timing
# ---------------------------------------------------------------------------
def track(endpoint_name: Optional[str] = None):
    """
    Decorator that automatically records request timing.

    Usage:
        @app.route("/describe", methods=["POST"])
        @track("/describe")
        def describe():
            ...
    """
    import functools
    from flask import request as flask_request

    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            name = endpoint_name or flask_request.path
            start = time.perf_counter()
            success = True
            try:
                result = f(*args, **kwargs)
                # Check for error responses
                if isinstance(result, tuple) and len(result) >= 2:
                    status = result[1]
                    if isinstance(status, int) and status >= 400:
                        success = False
                return result
            except Exception:
                success = False
                raise
            finally:
                elapsed = time.perf_counter() - start
                metrics.record(name, elapsed, success)
        return wrapper
    return decorator
