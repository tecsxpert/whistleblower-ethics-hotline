"""
Groq LLM client with retry logic, back-off, and PII-safe logging.
"""

import logging
import os
import time

import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"
MAX_RETRIES = 3
RETRY_BACKOFF = [1, 2, 4]
GROQ_TIMEOUT = int(os.getenv("GROQ_TIMEOUT_SECONDS", "25"))


def call_groq(
    prompt: str,
    temperature: float = 0.3,
    max_tokens: int = 1024,
    system_message: str | None = None,
) -> str:
    """Call the Groq chat-completions API with automatic retries.

    Returns the assistant's response text.
    Raises ``RuntimeError`` on permanent failures.
    """

    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not set or is empty.")

    messages: list[dict] = []
    if system_message:
        messages.append({"role": "system", "content": system_message})
    messages.append({"role": "user", "content": prompt})

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    last_exception: Exception | None = None

    for attempt in range(MAX_RETRIES):
        logger.info(
            "Groq API call attempt %d/%d (model=%s, temp=%s)",
            attempt + 1,
            MAX_RETRIES,
            GROQ_MODEL,
            temperature,
        )
        try:
            resp = requests.post(
                GROQ_API_URL,
                headers=headers,
                json=payload,
                timeout=GROQ_TIMEOUT,
            )

            # Immediate failures — no retry
            if resp.status_code in (401, 403):
                raise RuntimeError(
                    f"Groq API authentication error (HTTP {resp.status_code}). "
                    "Check your GROQ_API_KEY."
                )

            # Rate-limited — honour Retry-After
            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", RETRY_BACKOFF[attempt]))
                logger.warning(
                    "Groq API rate-limited (429). Retrying after %ds …", retry_after
                )
                time.sleep(retry_after)
                continue

            resp.raise_for_status()

            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            logger.info("Groq API responded (length=%d)", len(content))
            return content

        except requests.exceptions.Timeout as exc:
            logger.warning(
                "Groq API timeout on attempt %d/%d: %s",
                attempt + 1,
                MAX_RETRIES,
                exc,
            )
            last_exception = exc

        except requests.exceptions.HTTPError as exc:
            logger.warning(
                "Groq API HTTP error on attempt %d/%d: %s",
                attempt + 1,
                MAX_RETRIES,
                exc,
            )
            last_exception = exc

        except requests.exceptions.RequestException as exc:
            logger.warning(
                "Groq API request error on attempt %d/%d: %s",
                attempt + 1,
                MAX_RETRIES,
                exc,
            )
            last_exception = exc

        # Back-off before next attempt
        if attempt < MAX_RETRIES - 1:
            time.sleep(RETRY_BACKOFF[attempt])

    raise RuntimeError(
        f"Groq API failed after {MAX_RETRIES} attempts. Last error: {last_exception}"
    )
