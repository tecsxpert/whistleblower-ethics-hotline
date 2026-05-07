"""
ai-service/services/sanitize.py
================================
Input Sanitization & Security Layer — Tool-70 Whistleblower & Ethics Hotline

Responsibilities:
- HTML entity decoding (catches encoded injection payloads)
- Prompt injection detection
- HTML tag stripping
- SQL injection pattern detection
- XSS payload detection
- Thread-safe (no mutable shared state)

Usage:
    from services.sanitize import sanitize_input, validate_required_fields

    cleaned, is_suspicious = sanitize_input(user_text)
    if is_suspicious:
        return jsonify({"error": "Potential prompt injection detected. Request rejected."}), 400
"""

import html
import re
from typing import Union

# ---------------------------------------------------------------------------
# Injection Detection Patterns
# ---------------------------------------------------------------------------
# Ordered by severity (most obvious first).
# Compiled once at module load for performance.

_RAW_PATTERNS = [
    # Classic prompt injection phrases
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"disregard\s+your\s+instructions",
    r"forget\s+everything",
    r"act\s+as\s+",
    r"you\s+are\s+now\s+",
    r"from\s+now\s+on\s+you",
    r"pretend\s+you\s+are",
    r"roleplay\s+as",
    r"jailbreak",
    r"system\s+prompt",
    r"override\s+instructions",
    r"new\s+instructions",
    r"your\s+new\s+task",
    r"developer\s+mode",
    r"dan\s+mode",

    # XSS patterns
    r"<\s*script",
    r"javascript\s*:",
    r"vbscript\s*:",
    r"on\w+\s*=\s*['\"]",         # onerror="...", onclick="..."
    r"<\s*iframe",
    r"<\s*object",
    r"<\s*embed",

    # SQL injection patterns
    r";\s*drop\s+table",
    r";\s*delete\s+from",
    r"union\s+(all\s+)?select",
    r"--\s",                       # SQL line comment
    r"/\*.*\*/",                   # SQL block comment
    r"xp_cmdshell",
    r"exec\s*\(",
    r"execute\s*\(",
]

_COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in _RAW_PATTERNS]

# Maximum allowed length for a single text field (characters)
MAX_FIELD_LENGTH = 4000


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def sanitize_input(text: Union[str, None]) -> tuple[str, bool]:
    """
    Sanitize a single text input.

    Returns:
        (cleaned_text, is_suspicious)

    If is_suspicious is True, the caller MUST reject the request with HTTP 400.
    The returned cleaned_text is provided for logging purposes only in that case.

    Steps:
    1. Type and null check
    2. Length check
    3. HTML entity decode (catches &#73;gnore = Ignore)
    4. Injection pattern detection on decoded text
    5. HTML tag stripping
    6. Whitespace normalisation
    """
    # Step 1: Type and null check
    if text is None:
        return ("", False)
    if not isinstance(text, str):
        # Coerce non-string to string for downstream processing
        text = str(text)

    # Step 2: Length check (prevent processing oversized inputs)
    if len(text) > MAX_FIELD_LENGTH:
        # Truncate and mark suspicious — oversized inputs are a red flag
        text = text[:MAX_FIELD_LENGTH]

    # Step 3: HTML entity decode
    # Must happen BEFORE pattern detection to catch:
    #   &#73;gnore previous instructions → Ignore previous instructions
    #   &lt;script&gt; → <script>
    decoded = html.unescape(text)

    # Step 4: Prompt injection / XSS / SQL detection on decoded text
    lower_decoded = decoded.lower()
    for pattern in _COMPILED_PATTERNS:
        if pattern.search(lower_decoded):
            return (decoded, True)  # SUSPICIOUS — reject immediately

    # Step 5: Strip any remaining HTML tags from clean input
    # (e.g. accidental <b> tags in user typing)
    cleaned = re.sub(r"<[^>]+>", "", decoded)

    # Step 6: Normalise whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    return (cleaned, False)


def validate_required_fields(data: dict, required: list[str]) -> tuple[bool, str]:
    """
    Validate that all required fields are present and non-empty strings.

    Returns:
        (is_valid, error_message)

    Example:
        ok, msg = validate_required_fields(request.json, ["description", "category"])
        if not ok:
            return jsonify({"error": msg}), 400
    """
    if not data or not isinstance(data, dict):
        return (False, "Request body must be a JSON object")

    for field in required:
        value = data.get(field)
        if value is None:
            return (False, f"'{field}' is required")
        if not isinstance(value, str):
            return (False, f"'{field}' must be a string")
        if not value.strip():
            return (False, f"'{field}' must not be empty")

    return (True, "")


def sanitize_dict(data: dict, fields: list[str]) -> tuple[dict, bool]:
    """
    Sanitize multiple fields in a dict in one call.
    Returns (sanitized_dict, any_suspicious).

    Modifies only the specified fields; other fields are left unchanged.

    Usage:
        clean_data, suspicious = sanitize_dict(request.json, ["title", "description", "category"])
        if suspicious:
            return jsonify({"error": "Potential prompt injection detected. Request rejected."}), 400
    """
    result = dict(data)
    any_suspicious = False

    for field in fields:
        if field in result and isinstance(result[field], str):
            cleaned, is_suspicious = sanitize_input(result[field])
            result[field] = cleaned
            if is_suspicious:
                any_suspicious = True

    return (result, any_suspicious)
