"""
Tests for POST /recommend endpoint.
"""

import json
from unittest.mock import patch

from tests.conftest import MOCK_DESCRIBE_RESPONSE, MOCK_RECOMMEND_RESPONSE


class TestRecommend:
    """Test suite for the /recommend endpoint."""

    def test_recommend_valid_input(self, client):
        """Valid text returns 200 with exactly 3 recommendations."""
        with patch("routes.recommend.call_groq") as mock_groq:
            # First call → describe analysis, second call → recommendations
            mock_groq.side_effect = [MOCK_DESCRIBE_RESPONSE, MOCK_RECOMMEND_RESPONSE]

            resp = client.post(
                "/recommend/",
                json={"text": "I witnessed my manager approving fake invoices worth $50,000 to a shell company owned by his brother-in-law."},
            )

        assert resp.status_code == 200
        data = resp.get_json()
        assert "recommendations" in data
        assert len(data["recommendations"]) == 3
        for rec in data["recommendations"]:
            assert "action_type" in rec
            assert "description" in rec
            assert "priority" in rec
            assert "responsible_party" in rec
        assert data["is_fallback"] is False

    def test_recommend_groq_failure(self, client):
        """When Groq is down, returns fallback with is_fallback=True."""
        with patch("routes.recommend.call_groq", return_value=None):
            resp = client.post(
                "/recommend/",
                json={"text": "Test complaint about workplace safety violations."},
            )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["is_fallback"] is True
        assert len(data["recommendations"]) == 3
