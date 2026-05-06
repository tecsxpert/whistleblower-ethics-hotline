"""
Groq LLM client — calls the Llama-3.3-70b-versatile model via the
Groq REST API with retry logic and prompt template loading.
services/groq_client.py
Groq API client with retry logic, exponential backoff, and granular error handling.

Validates the API key at module import time so misconfiguration is caught
at startup rather than on the first live request.
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
import requests
from typing import Optional
from pathlib import Path

from dotenv import load_dotenv

# I-8 FIX: Call load_dotenv() here so _GROQ_API_KEY is populated correctly
# regardless of whether groq_client is imported before or after create_app().
# load_dotenv() is idempotent — calling it multiple times is safe.
# Use explicit path so it works regardless of CWD.
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_env_path)

logger = logging.getLogger(__name__)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"
MAX_RETRIES = 3
RETRY_BACKOFF = (1, 2, 4)  # seconds — tuple for immutability
REQUEST_TIMEOUT = 30  # seconds — named constant for HTTP timeout

# Fix #12: Read and validate at module import time — fail fast on missing key.
# NOTE: This is a module-level snapshot.  In containerised deployments, restart
# the container to pick up a rotated key.
_GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

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

def call_groq(
    prompt: str,
    temperature: float = 0.3,
    max_tokens: int = 1024,
    system_message: Optional[str] = None,
) -> str:
    """
    Call the Groq API with retry + exponential backoff.

    Args:
        prompt:         User-role message content (the main prompt).
        temperature:    Sampling temperature (0.0–1.0).
        max_tokens:     Maximum tokens in the response.
        system_message: Optional system-role message prepended to the conversation.
                        Used by the RAG /query endpoint to inject retrieved context.

    Returns:
        The raw text content of the model response.
    Raises:
        RuntimeError if all retries fail or the API key is invalid/missing.
    """
    if not _GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY environment variable is not set.")

    headers = {
        "Authorization": f"Bearer {_GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    messages = []
    if system_message:
        messages.append({"role": "system", "content": system_message})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": GROQ_MODEL,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "messages": messages,
    }

    last_error: Optional[Exception] = None

    # HI-3 FIX: Use a while loop with an explicit attempt counter so that 429
    # rate-limit responses do NOT consume one of the MAX_RETRIES slots.
    # The old `for attempt, wait in enumerate(RETRY_BACKOFF)` always advanced
    # the iterator even on `continue`, exhausting retries after 3 rate-limits.
    attempt = 0
    while attempt < MAX_RETRIES:
        wait = RETRY_BACKOFF[attempt] if attempt < len(RETRY_BACKOFF) else RETRY_BACKOFF[-1]
        logger.debug(
            "Groq API call attempt %d/%d (model=%s, temp=%.1f)",
            attempt + 1, MAX_RETRIES, GROQ_MODEL, temperature,
        )
        try:
            response = requests.post(
                GROQ_API_URL, headers=headers, json=payload, timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            logger.info("Groq call succeeded on attempt %d", attempt + 1)
            return content

        except requests.exceptions.Timeout as exc:
            last_error = exc
            logger.warning("Groq attempt %d timed out, retrying …", attempt + 1)

        except requests.exceptions.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else 0
            if status in (401, 403):
                raise RuntimeError(
                    "Groq API key is invalid or unauthorised."
                ) from exc
            # I-2 FIX: On 429 (rate limited), honour Retry-After and do NOT count
            # this attempt against MAX_RETRIES — retrying too early wastes quota.
            if status == 429:
                try:
                    retry_after = int(
                        exc.response.headers.get("Retry-After", wait)
                    )
                except (ValueError, TypeError):
                    retry_after = wait
                logger.warning(
                    "Groq 429 rate-limited on attempt %d — sleeping %ds (Retry-After)",
                    attempt + 1, retry_after,
                )
                time.sleep(retry_after)
                # Do NOT increment attempt — 429 is not a real failure
                continue
            last_error = exc
            logger.warning(
                "Groq HTTP error %d on attempt %d/%d", status, attempt + 1, MAX_RETRIES
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
        except requests.exceptions.RequestException as exc:
            last_error = exc
            logger.warning(
                "Groq network error on attempt %d/%d: %s", attempt + 1, MAX_RETRIES, exc
            )

        attempt += 1
        if attempt < MAX_RETRIES:
            time.sleep(wait)

    raise RuntimeError(
        f"Groq API failed after {MAX_RETRIES} attempts: {last_error}"
    )
