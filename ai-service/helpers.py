"""
Utility helpers — JSON extraction and field validation.
"""

import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def extract_json(text: str) -> Optional[dict | list]:
    """
    Extract the first complete JSON object **or** array from *text*
    using brace/bracket-depth counting.

    Returns the parsed dict/list, or ``None`` on failure.
    """
    if not text:
        logger.warning("extract_json called with empty text.")
        return None

    start_char = None
    end_char = None
    start_idx = None
    depth = 0

    for i, ch in enumerate(text):
        if start_idx is None:
            if ch == '{':
                start_char, end_char = '{', '}'
                start_idx = i
                depth = 1
            elif ch == '[':
                start_char, end_char = '[', ']'
                start_idx = i
                depth = 1
        else:
            if ch == start_char:
                depth += 1
            elif ch == end_char:
                depth -= 1
            if depth == 0:
                json_str = text[start_idx: i + 1]
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError as exc:
                    logger.warning("JSON decode failed: %s", exc)
                    return None

    logger.warning("No complete JSON structure found in model output.")
    return None


def validate_required_fields(data: dict, fields: list[str]) -> list[str]:
    """
    Return a list of field names that are missing or empty-string in *data*.
    """
    missing: list[str] = []
    for field in fields:
        value = data.get(field)
        if value is None or (isinstance(value, str) and value.strip() == ""):
            missing.append(field)
    return missing
