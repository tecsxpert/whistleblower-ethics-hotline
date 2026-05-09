"""
Tests for GET /health endpoint (V2 architecture).
"""

from unittest.mock import patch


class TestHealth:
    """Test suite for the /health endpoint."""

    def test_health_endpoint(self, client):
        """GET /health returns 200 with all required fields."""
        with patch("routes.health.is_redis_connected", return_value=True), \
             patch("routes.health.is_chromadb_connected", return_value=True), \
             patch("routes.health.document_count", return_value=10):
            resp = client.get("/health")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "ok"
        assert data["model"] == "llama-3.3-70b-versatile"
        assert "uptime_seconds" in data
        assert data["redis_connected"] is True
        assert data["chromadb_connected"] is True
        assert isinstance(data["endpoints"], dict)
        assert "/describe" in data["available_endpoints"]
        assert "/recommend" in data["available_endpoints"]
        assert "/generate-report" in data["available_endpoints"]
        assert "/health" in data["available_endpoints"]
        assert data["rate_limit"] == "30 per minute"
        assert data["cache_ttl_seconds"] == 900

    def test_health_degraded_without_redis(self, client):
        """GET /health returns degraded status when Redis is unavailable."""
        with patch("routes.health.is_redis_connected", return_value=False), \
             patch("routes.health.is_chromadb_connected", return_value=True), \
             patch("routes.health.document_count", return_value=10):
            resp = client.get("/health")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "degraded"
        assert data["redis_connected"] is False
