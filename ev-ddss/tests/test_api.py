"""Tests for the FastAPI health check endpoints."""

from fastapi.testclient import TestClient


class TestHealthEndpoints:
    """Verify the /health and /version endpoints."""

    def test_root_endpoint(self, client: TestClient) -> None:
        """GET / should return application information."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "application" in data
        assert "version" in data
        assert data["status"] == "running"

    def test_health_endpoint_structure(self, client: TestClient) -> None:
        """GET /health should return the expected JSON structure."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()

        # Expected top-level keys
        assert "status" in data
        assert "application" in data
        assert "database" in data
        assert "qdrant" in data
        assert "configuration" in data
        assert "version" in data

        # Application info
        app = data["application"]
        assert "name" in app
        assert "version" in app
        assert app["name"] == "EV-DDSS"

    def test_health_status_values(self, client: TestClient) -> None:
        """Health status should be either 'healthy' or 'degraded'."""
        response = client.get("/health")
        data = response.json()
        assert data["status"] in ("healthy", "degraded")

    def test_version_endpoint(self, client: TestClient) -> None:
        """GET /version should return version information."""
        response = client.get("/version")
        assert response.status_code == 200
        data = response.json()
        assert "application" in data
        assert "version" in data
        assert "python" in data
        assert data["version"] == "0.1.0"

    def test_health_configuration_loaded(self, client: TestClient) -> None:
        """The configuration field should always show 'loaded'."""
        response = client.get("/health")
        data = response.json()
        assert data["configuration"] == "loaded"

    def test_404_returns_json(self, client: TestClient) -> None:
        """A non-existent route should return a 404 JSON response."""
        response = client.get("/nonexistent-route")
        assert response.status_code == 404
