"""
Tests for POST /generate-report endpoint.
"""

import json
from unittest.mock import patch

from tests.conftest import (
    MOCK_DESCRIBE_RESPONSE,
    MOCK_RECOMMEND_RESPONSE,
    MOCK_REPORT_RESPONSE,
)


class TestReport:
    """Test suite for the /generate-report endpoint."""

    def test_report_valid_input(self, client):
        """Valid text returns 200 with all required report fields."""
        with patch("routes.report.call_groq") as mock_groq:
            # Three internal calls: describe → recommend → report
            mock_groq.side_effect = [
                MOCK_DESCRIBE_RESPONSE,
                MOCK_RECOMMEND_RESPONSE,
                MOCK_REPORT_RESPONSE,
            ]

            resp = client.post(
                "/generate-report/",
                json={"text": "I witnessed my manager approving fake invoices worth $50,000 to a shell company owned by his brother-in-law."},
            )

        assert resp.status_code == 200
        data = resp.get_json()
        assert "title" in data
        assert "summary" in data
        assert "overview" in data
        assert isinstance(data["key_items"], list)
        assert len(data["key_items"]) >= 4
        assert isinstance(data["recommendations"], list)
        assert len(data["recommendations"]) >= 3
        assert data["risk_level"] in ("Low", "Medium", "High", "Critical")
        assert isinstance(data["estimated_resolution_days"], int)
        assert "generated_at" in data
        assert data["is_fallback"] is False

    def test_report_groq_failure(self, client):
        """When Groq is down, returns fallback with is_fallback=True."""
        with patch("routes.report.call_groq", return_value=None):
            resp = client.post(
                "/generate-report/",
                json={"text": "Test complaint about bribery."},
            )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["is_fallback"] is True
        assert "title" in data
        assert "summary" in data
        assert "key_items" in data
        assert "recommendations" in data
        assert "estimated_resolution_days" in data
