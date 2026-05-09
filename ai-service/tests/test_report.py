"""
Tests for POST /generate-report endpoint (V2 architecture).
"""

from unittest.mock import patch

from tests.conftest import MOCK_REPORT_RESPONSE


class TestReport:
    """Test suite for the /generate-report endpoint."""

    def test_report_valid_input(self, client):
        """Valid text returns 200 with all required report fields."""
        with patch("routes.report.call_groq", return_value=MOCK_REPORT_RESPONSE):
            resp = client.post(
                "/generate-report",
                json={
                    "text": (
                        "I witnessed my manager approving fake invoices "
                        "worth $50,000 to a shell company owned by his "
                        "brother-in-law."
                    )
                },
            )

        assert resp.status_code == 200
        data = resp.get_json()
        assert "title" in data
        assert "summary" in data
        assert "overview" in data
        assert isinstance(data["key_items"], list)
        assert len(data["key_items"]) >= 2
        assert isinstance(data["recommendations"], list)
        assert len(data["recommendations"]) >= 3
        assert "generated_at" in data
        assert data["is_fallback"] is False

    def test_report_groq_failure(self, client):
        """When Groq raises RuntimeError, returns fallback with is_fallback=True."""
        with patch("routes.report.call_groq", side_effect=RuntimeError("Groq down")):
            resp = client.post(
                "/generate-report",
                json={"text": "Test complaint about bribery."},
            )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["is_fallback"] is True
        assert "title" in data
        assert "summary" in data
        assert "key_items" in data
        assert "recommendations" in data
        assert "generated_at" in data
