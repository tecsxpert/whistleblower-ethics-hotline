"""
Tests for POST /recommend endpoint (V2 architecture).
"""

from unittest.mock import patch

from tests.conftest import MOCK_RECOMMEND_RESPONSE


class TestRecommend:
    """Test suite for the /recommend endpoint."""

    def test_recommend_valid_input(self, client):
        """Valid text returns 200 with exactly 3 recommendations."""
        with patch("routes.recommend.call_groq", return_value=MOCK_RECOMMEND_RESPONSE):
            resp = client.post(
                "/recommend",
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
        assert "recommendations" in data
        assert len(data["recommendations"]) == 3
        for rec in data["recommendations"]:
            assert "action_type" in rec
            assert "description" in rec
            assert rec["priority"] in {"High", "Medium", "Low"}
        assert data["is_fallback"] is False
        assert "generated_at" in data

    def test_recommend_groq_failure(self, client):
        """When Groq raises RuntimeError, returns fallback with is_fallback=True."""
        with patch("routes.recommend.call_groq", side_effect=RuntimeError("Groq down")):
            resp = client.post(
                "/recommend",
                json={"text": "Test complaint about workplace safety violations."},
            )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["is_fallback"] is True
        assert len(data["recommendations"]) == 3
        assert "generated_at" in data
