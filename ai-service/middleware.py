"""
Input sanitisation and prompt-injection detection middleware.

Backward-compatible wrapper — delegates to the production-grade
sanitizer in services/sanitize.py.  All existing route imports
(``from middleware import sanitize_input``) continue to work unchanged.
"""

import logging

from services.sanitize import sanitize_input  # noqa: F401 — re-export

logger = logging.getLogger(__name__)
