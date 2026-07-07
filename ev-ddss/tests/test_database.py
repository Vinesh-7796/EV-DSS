"""Tests for the database connection module.

These tests verify the DatabaseManager lifecycle and error handling.
Actual connectivity tests require a running PostgreSQL instance.
"""

import pytest

from database.connection import DatabaseManager


class TestDatabaseManager:
    """Verify DatabaseManager behavior."""

    def test_initialization(self) -> None:
        """A new DatabaseManager should start in disconnected state."""
        db = DatabaseManager("postgresql://test:test@localhost:5432/test")
        assert db.is_connected is False

    def test_connect_no_server(self) -> None:
        """Connecting to an unreachable server should raise."""
        db = DatabaseManager("postgresql://nobody:nobody@localhost:19999/nonexistent")
        with pytest.raises(Exception):
            db.connect()
        assert db.is_connected is False

    def test_disconnect_when_not_connected(self) -> None:
        """Disconnecting when not connected should not raise."""
        db = DatabaseManager()
        db.disconnect()  # Should be a no-op
        assert db.is_connected is False

    def test_get_session_before_connect(self) -> None:
        """Getting a session before connect() should raise RuntimeError."""
        db = DatabaseManager()
        with pytest.raises(RuntimeError, match="not connected"):
            with db.get_session():
                pass

    def test_database_url_conversion(self) -> None:
        """Database URL should be stored as provided."""
        url = "postgresql://user:pass@remote:5432/db"
        db = DatabaseManager(url)
        assert db._database_url == url

    @pytest.mark.skip(reason="Requires running PostgreSQL instance")
    def test_connect_and_disconnect(self) -> None:
        """End-to-end connect/disconnect with a real database."""
        db = DatabaseManager()
        db.connect()
        assert db.is_connected is True
        db.disconnect()
        assert db.is_connected is False
