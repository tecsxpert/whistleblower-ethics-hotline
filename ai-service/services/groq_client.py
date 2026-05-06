"""
Groq LLM client — calls the Llama-3.3-70b-versatile model via the
Groq REST API with retry logic and prompt template loading.
"""

import os
import time
import logging
from pathlib import Path
from typing import Optional

import requests as http_requests

from services.metrics import last_100_response_times, metrics_lock

logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────────
MODEL_NAME: str = "llama-3.3-70b-versatile"
MAX_RETRIES: int = 3
RETRY_BACKOFF: list[int] = [1, 2, 4]
_GROQ_URL: str = "https://api.groq.com/openai/v1/chat/completions"
_TIMEOUT: int = 10  # seconds

# ── Prompt template cache ────────────────────────────────────────────
_prompt_cache: dict[str, str] = {}


def load_prompt(filename: str) -> str:
    """
    Load a prompt template from the ``prompts/`` directory (relative to
    this file).  Results are cached in ``_prompt_cache``.
    """
    if filename in _prompt_cache:
        return _prompt_cache[filename]

    prompts_dir = Path(__file__).resolve().parent.parent / "prompts"
    filepath = prompts_dir / filename
    text = filepath.read_text(encoding="utf-8")
    _prompt_cache[filename] = text
    logger.info("Loaded prompt template: %s", filename)
    return text


def call_groq(
    prompt: str,
    temperature: float = 0.3,
    max_tokens: int = 1024,
) -> Optional[str]:
    """
    Send a chat-completion request to the Groq API.

    Returns the assistant message content (str) or ``None`` if all
    retries are exhausted or the API key is missing.
    """
    # Read API key inside the function — not at module top level —
    # so tests that don't set the env var can still import this module.
    api_key = os.getenv("GROQ_API_KEY", "")

    if not api_key:
        logger.error("GROQ_API_KEY is not set — cannot call Groq API.")
        return None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    body = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an expert ethics-compliance AI assistant. "
                    "Always respond with the exact JSON structure requested. "
                    "Never include markdown, backticks, or explanatory text."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    for attempt in range(MAX_RETRIES):
        try:
            start = time.time()
            resp = http_requests.post(
                _GROQ_URL,
                headers=headers,
                json=body,
                timeout=_TIMEOUT,
            )
            elapsed_ms = (time.time() - start) * 1000

            # Track response time — thread-safe via lock + bounded deque
            with metrics_lock:
                last_100_response_times.append(elapsed_ms)

            # Rate-limited — honour Retry-After
            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", RETRY_BACKOFF[attempt]))
                logger.warning(
                    "Groq 429 — retrying in %ds (attempt %d/%d)",
                    retry_after,
                    attempt + 1,
                    MAX_RETRIES,
                )
                time.sleep(retry_after)
                continue

            resp.raise_for_status()

            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            logger.info(
                "Groq response received (%.0f ms, attempt %d)",
                elapsed_ms,
                attempt + 1,
            )
            return content

        except http_requests.exceptions.Timeout:
            logger.warning(
                "Groq timeout — retrying in %ds (attempt %d/%d)",
                RETRY_BACKOFF[attempt],
                attempt + 1,
                MAX_RETRIES,
            )
            time.sleep(RETRY_BACKOFF[attempt])

        except http_requests.exceptions.RequestException:
            logger.exception(
                "Groq request error (attempt %d/%d)",
                attempt + 1,
                MAX_RETRIES,
            )
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_BACKOFF[attempt])

    logger.error("All %d Groq retries exhausted — returning None.", MAX_RETRIES)
    return None
