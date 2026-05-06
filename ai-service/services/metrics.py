"""
Shared response-time tracking — thread-safe deque with lock.
Isolated in its own module to prevent circular imports between
groq_client.py and routes/health.py.
"""

from collections import deque
from threading import Lock

last_100_response_times: deque = deque(maxlen=100)
metrics_lock = Lock()
