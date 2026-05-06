"""
Tests for GET /health endpoint.
"""

from unittest.mock import patch


class TestHealth:
    """Test suite for the /health endpoint."""

    def test_health_endpoint(self, client):
        """GET /health returns 200 with all required fields."""
        with patch("routes.health.is_redis_connected", return_value=True), \
             patch("routes.health.is_chromadb_connected", return_value=True):
            resp = client.get("/health/")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "healthy"
        assert data["model"] == "llama-3.3-70b-versatile"
        assert "uptime_seconds" in data
        assert isinstance(data["uptime_seconds"], float)
        assert "avg_response_ms" in data
        assert isinstance(data["avg_response_ms"], float)
        assert data["redis_connected"] is True
        assert data["chromadb_connected"] is True
        assert "/describe" in data["endpoints"]
        assert "/recommend" in data["endpoints"]
        assert "/generate-report" in data["endpoints"]
        assert "/health" in data["endpoints"]
        assert data["rate_limit"] == "30 per minute"
        assert data["cache_ttl_seconds"] == 900
