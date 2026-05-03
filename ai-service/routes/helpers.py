"""
Shared helpers for route handlers: prompt loading, input sanitisation,
JSON extraction, and truncation.
"""

import html
import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt loading
# ---------------------------------------------------------------------------
PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
_prompt_cache: dict[str, str] = {}


def load_prompt(filename: str) -> str:
    """Load a prompt template from disk (cached after first read)."""
    if filename in _prompt_cache:
        return _prompt_cache[filename]

    filepath = PROMPTS_DIR / filename
    try:
        content = filepath.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise RuntimeError(f"Prompt file not found: {filename}")

    _prompt_cache[filename] = content
    return content


# ---------------------------------------------------------------------------
# Truncation
# ---------------------------------------------------------------------------
PROMPT_INPUT_MAX_CHARS = 2000


def truncate_for_prompt(text: str, max_chars: int = PROMPT_INPUT_MAX_CHARS) -> str:
    """Truncate text for safe prompt inclusion."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + " [input truncated for processing]"


# ---------------------------------------------------------------------------
# Injection detection
# ---------------------------------------------------------------------------
_INJECTION_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"ignore\s+(all\s+)?previous\s+instructions",
        r"disregard\s+(all\s+)?previous",
        r"you\s+are\s+now\s+",
        r"act\s+as\s+(a\s+)?(?:different|new|another)",
        r"forget\s+(everything|all)",
        r"system\s*:\s*",
        r"<\s*/?(?:script|iframe|object|embed|form|img|svg|input|button|link|meta)",
        r"javascript\s*:",
        r"data\s*:\s*text/html",
        r"on\w+\s*=",
        r"prompt\s*injection",
        r"jailbreak",
        r"dan\s+mode",
        r"developer\s+mode",
        r"override\s+(all\s+)?instructions",
        r"new\s+instructions\s*:",
        r'(\{|\[)\s*"role"\s*:',
        r"<\|(?:im_start|im_end|endoftext)\|>",
    ]
]


def sanitise_input(text: str) -> str:
    """Sanitise user input: unescape HTML entities, strip tags, detect injections.

    Raises ``ValueError`` if a prompt-injection pattern is detected.
    Returns the cleaned string.
    """
    # Unescape HTML entities
    text = html.unescape(text)

    # Strip HTML tags
    text = re.sub(r"<[^>]*>", "", text)

    # Check injection patterns
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            raise ValueError("Input contains a disallowed pattern.")

    return text


# ---------------------------------------------------------------------------
# JSON extraction
# ---------------------------------------------------------------------------


def extract_json(raw: str) -> dict:
    """Extract the first valid JSON object from a raw LLM response.

    Strips markdown fences, finds the first ``{``, then uses brace-depth
    counting to locate the matching ``}``.

    Raises ``ValueError`` if no valid JSON object can be found.
    """
    # Strip markdown fences
    cleaned = re.sub(r"```(?:json)?\s*", "", raw)
    cleaned = cleaned.replace("```", "")

    # Find first opening brace
    start = cleaned.find("{")
    if start == -1:
        raise ValueError("No JSON object found in response.")

    # Brace-depth counter
    depth = 0
    in_string = False
    escape = False
    end = start

    for i in range(start, len(cleaned)):
        ch = cleaned[i]

        if escape:
            escape = False
            continue

        if ch == "\\" and in_string:
            escape = True
            continue

        if ch == '"' and not escape:
            in_string = not in_string
            continue

        if in_string:
            continue

        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i
                break

    if depth != 0:
        raise ValueError("Unbalanced braces in JSON response.")

    json_str = cleaned[start : end + 1]

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc}") from exc
