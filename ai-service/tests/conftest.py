"""
Shared pytest fixtures for the Tool-70 test suite.
All Groq calls are fully mocked — no real API traffic.
"""

import json
import os

# ── Set env vars BEFORE any app import ────────────────────────────────
os.environ.setdefault("GROQ_API_KEY", "test_key_for_pytest")
os.environ.setdefault("REDIS_URL", "")

import pytest
from unittest.mock import patch

from app import create_app


# ── Valid mock responses (V2 architecture) ────────────────────────────
MOCK_DESCRIBE_RESPONSE = json.dumps({
    "category": "Financial Fraud",
    "severity": "Critical",
    "summary": (
        "An employee witnessed fraudulent invoice approvals totalling "
        "$50,000 directed to a shell company with familial ties to the "
        "approving manager."
    ),
    "key_entities": [
        "Manager",
        "Shell company",
        "Brother-in-law",
    ],
    "recommended_action": (
        "Immediately escalate to the legal department and initiate a "
        "forensic audit of all invoices approved by the manager."
    ),
})

MOCK_RECOMMEND_RESPONSE = json.dumps({
    "recommendations": [
        {
            "action_type": "Investigation",
            "description": (
                "Conduct a forensic audit of all invoices approved by "
                "the implicated manager over the past 12 months."
            ),
            "priority": "High",
        },
        {
            "action_type": "Escalation",
            "description": (
                "Escalate findings to the Chief Compliance Officer "
                "and Board of Directors."
            ),
            "priority": "Medium",
        },
        {
            "action_type": "Documentation",
            "description": (
                "Preserve all financial records, emails, and "
                "communications related to the shell company."
            ),
            "priority": "Low",
        },
    ]
})

MOCK_REPORT_RESPONSE = json.dumps({
    "title": "Investigation Report: Suspected Fraudulent Invoice Scheme",
    "summary": (
        "A whistleblower report alleges systematic invoice fraud "
        "involving a manager and a related-party shell company."
    ),
    "overview": (
        "The complaint details a scheme where a manager approved "
        "fraudulent invoices totalling $50,000 to a shell company "
        "owned by his brother-in-law. This constitutes a potential "
        "conflict of interest and financial fraud. A full forensic "
        "audit and employee interviews are warranted."
    ),
    "key_items": [
        "Fraudulent invoices totalling $50,000 identified",
        "Shell company linked to manager's brother-in-law",
        "Potential conflict of interest violation",
        "Possible ongoing scheme requiring historical review",
    ],
    "recommendations": [
        "Initiate forensic audit of manager's approved transactions",
        "Engage external counsel for independent investigation",
        "Implement whistleblower protection measures",
    ],
})


@pytest.fixture
def app():
    """Create a Flask test application."""
    application = create_app()
    application.config["TESTING"] = True
    return application


@pytest.fixture
def client(app):
    """Create a Flask test client."""
    return app.test_client()


@pytest.fixture(autouse=True)
def mock_cache():
    """Mock Redis cache at the ROUTE level where it is used.

    Patching at 'services.cache.cache_get' does NOT work because each
    route module has already bound a local reference via
    'from services.cache import cache_get'.
    """
    with patch("routes.describe.cache_get", return_value=None), \
         patch("routes.describe.cache_set"), \
         patch("routes.recommend.cache_get", return_value=None), \
         patch("routes.recommend.cache_set"), \
         patch("routes.report.cache_get", return_value=None), \
         patch("routes.report.cache_set"), \
         patch("routes.query.cache_get", return_value=None), \
         patch("routes.query.cache_set"):
        yield
