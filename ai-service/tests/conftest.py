"""
Pytest fixtures for the AI microservice test suite.
"""

import json
import os
from unittest.mock import MagicMock

import pytest

# Set env vars BEFORE any app import
os.environ["SKIP_GROQ_VALIDATION"] = "true"
os.environ["GROQ_API_KEY"] = "test-key"
os.environ["CHROMA_PERSIST_DIR"] = "./test_chroma_data"


@pytest.fixture
def client():
    """Flask test client with TESTING=True."""
    from app import create_app

    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture
def mock_groq_success():
    """MagicMock simulating a successful Groq HTTP response."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "category": "Fraud",
                            "severity": "High",
                            "summary": "Employee reported financial irregularities.",
                            "key_entities": ["Finance Department", "Q3 Reports"],
                            "recommended_action": "Initiate formal investigation.",
                            "generated_at": "2024-01-01T00:00:00Z",
                            "is_fallback": False,
                        }
                    )
                }
            }
        ]
    }
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


@pytest.fixture
def sample_report_text():
    """Sample expense fraud report text."""
    return (
        "I have discovered that my manager has been submitting false expense reports "
        "for the past six months. The total amount of fraudulent claims exceeds $50,000. "
        "I have copies of the original receipts that show the actual amounts were much lower "
        "than what was submitted. This has been going on since January 2024."
    )


@pytest.fixture
def sample_harassment_text():
    """Sample workplace harassment report text."""
    return (
        "I want to report ongoing harassment by a senior colleague in the marketing "
        "department. They have been making inappropriate comments about my appearance "
        "and sending unwanted messages after work hours. I have screenshots of the "
        "messages and two colleagues who witnessed the verbal comments."
    )
