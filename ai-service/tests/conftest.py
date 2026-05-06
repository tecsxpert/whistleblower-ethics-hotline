"""
Shared pytest fixtures for the Tool-70 test suite.
All Groq calls are fully mocked — no real API traffic.
"""

import json
import os

# ── Set env vars BEFORE any app import ────────────────────────────────
os.environ.setdefault("GROQ_API_KEY", "test_key_for_pytest")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")

import pytest
from unittest.mock import patch, MagicMock

from app import create_app


# ── Valid mock responses ─────────────────────────────────────────────
MOCK_DESCRIBE_RESPONSE = json.dumps({
    "category": "Financial Fraud",
    "severity": "Critical",
    "summary": "An employee witnessed fraudulent invoice approvals totalling $50,000 directed to a shell company with familial ties to the approving manager.",
    "key_facts": [
        "Manager approved fake invoices",
        "Invoices worth $50,000",
        "Shell company owned by manager's brother-in-law"
    ],
    "recommended_action": "Immediately escalate to the legal department and initiate a forensic audit of all invoices approved by the manager.",
    "confidence_score": 0.95
})

MOCK_RECOMMEND_RESPONSE = json.dumps([
    {
        "action_type": "Investigate",
        "description": "Conduct a forensic audit of all invoices approved by the implicated manager over the past 12 months.",
        "priority": "Immediate",
        "responsible_party": "Legal Team"
    },
    {
        "action_type": "Escalate",
        "description": "Escalate findings to the Chief Compliance Officer and Board of Directors.",
        "priority": "Within 24 Hours",
        "responsible_party": "Ethics Committee"
    },
    {
        "action_type": "Document",
        "description": "Preserve all financial records, emails, and communications related to the shell company transactions.",
        "priority": "Immediate",
        "responsible_party": "HR Department"
    }
])

MOCK_REPORT_RESPONSE = json.dumps({
    "title": "Investigation Report: Suspected Fraudulent Invoice Scheme",
    "summary": "A whistleblower report alleges systematic invoice fraud involving a manager and a related-party shell company. Immediate investigation is recommended.",
    "overview": "The complaint details a scheme where a manager approved fraudulent invoices totalling $50,000 to a shell company owned by his brother-in-law. This constitutes a potential conflict of interest and financial fraud. The pattern suggests this may not be an isolated incident. A full forensic audit and employee interviews are warranted. Protective measures for the whistleblower should be enacted immediately.",
    "key_items": [
        "Fraudulent invoices totalling $50,000 identified",
        "Shell company linked to manager's brother-in-law",
        "Potential conflict of interest violation",
        "Possible ongoing scheme requiring historical review"
    ],
    "recommendations": [
        "Initiate forensic audit of manager's approved transactions",
        "Engage external counsel for independent investigation",
        "Implement whistleblower protection measures"
    ],
    "risk_level": "Critical",
    "estimated_resolution_days": 45
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
    with patch("routes.describe.cache_get", return_value=None) as d_get, \
         patch("routes.describe.cache_set") as d_set, \
         patch("routes.recommend.cache_get", return_value=None) as r_get, \
         patch("routes.recommend.cache_set") as r_set, \
         patch("routes.report.cache_get", return_value=None) as rp_get, \
         patch("routes.report.cache_set") as rp_set:
        yield {
            "describe_get": d_get, "describe_set": d_set,
            "recommend_get": r_get, "recommend_set": r_set,
            "report_get": rp_get, "report_set": rp_set,
        }


@pytest.fixture(autouse=True)
def mock_vector_store():
    """Mock ChromaDB queries at the ROUTE level where they are used.

    Each route imports query_knowledge directly, creating a local
    binding.  We must patch where used, not where defined.
    """
    with patch("routes.describe.query_knowledge", return_value=[]), \
         patch("routes.recommend.query_knowledge", return_value=[]), \
         patch("routes.report.query_knowledge", return_value=[]):
        yield
