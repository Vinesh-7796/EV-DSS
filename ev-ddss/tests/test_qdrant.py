"""Tests for the Qdrant connection module.

These tests verify the QdrantManager lifecycle and error handling.
Actual connectivity tests require a running Qdrant instance.
"""

import pytest

from database.qdrant import QdrantManager


class TestQdrantManager:
    """Verify QdrantManager behavior."""

    def test_initialization(self) -> None:
        """A new QdrantManager should start in disconnected state."""
        qdrant = QdrantManager()
        assert qdrant.is_connected is False

    def test_connect_no_server(self) -> None:
        """Connecting to an unreachable server should raise."""
        qdrant = QdrantManager(url="http://localhost:19999")
        with pytest.raises(ConnectionError):
            qdrant.connect()
        assert qdrant.is_connected is False

    def test_health_check_before_connect(self) -> None:
        """Health check before connect should return disconnected status."""
        qdrant = QdrantManager()
        result = qdrant.health_check()
        assert result["status"] == "disconnected"

    def test_list_collections_before_connect(self) -> None:
        """Listing collections before connect should raise RuntimeError."""
        qdrant = QdrantManager()
        with pytest.raises(RuntimeError, match="not connected"):
            qdrant.list_collections()

    def test_disconnect_when_not_connected(self) -> None:
        """Disconnecting when not connected should not raise."""
        qdrant = QdrantManager()
        qdrant.disconnect()  # Should be a no-op
        assert qdrant.is_connected is False

    @pytest.mark.skip(reason="Requires running Qdrant instance")
    def test_connect_and_health_check(self) -> None:
        """End-to-end connect and health check with a real Qdrant server."""
        qdrant = QdrantManager()
        qdrant.connect()
        assert qdrant.is_connected is True
        health = qdrant.health_check()
        assert health["status"] == "healthy"
        assert "collections" in health
        qdrant.disconnect()
        assert qdrant.is_connected is False
