"""
Input sanitisation and prompt-injection detection middleware.
"""

import re
import html
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

# ── Prompt-injection patterns (case-insensitive) ─────────────────────
_INJECTION_PATTERNS: list[str] = [
    "ignore previous instructions",
    "you are now",
    "act as",
    "disregard",
    "forget your",
    "new instruction",
    "system prompt",
    "<script",
    "jailbreak",
    "roleplay as",
    "developer mode",
    "bypass",
    "simulate",
    "override",
    "reveal prompt",
    "pretend to be",
]

MAX_INPUT_LENGTH = 5000


def sanitize_input(text: str) -> Tuple[str, bool]:
    """
    Sanitise user-supplied text.

    Returns
    -------
    (sanitized_text, is_injection)
        sanitized_text — HTML-unescaped, tag-stripped, truncated string.
        is_injection   — True when a prompt-injection pattern is detected.
    """
    # 1. Decode HTML entities BEFORE stripping tags
    sanitized = html.unescape(text)

    # 2. Strip HTML tags
    sanitized = re.sub(r"<[^>]*>", "", sanitized)

    # 3. Detect prompt injection
    lower = sanitized.lower()
    is_injection = any(pattern in lower for pattern in _INJECTION_PATTERNS)

    if is_injection:
        logger.warning("Prompt-injection attempt detected in input.")

    # 4. Truncate to max length AFTER sanitisation
    sanitized = sanitized[:MAX_INPUT_LENGTH]

    return sanitized, is_injection
