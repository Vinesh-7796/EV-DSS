"""Tests for the configuration module."""

from config import Settings, get_settings


class TestSettings:
    """Verify configuration loading and defaults."""

    def test_settings_singleton(self) -> None:
        """get_settings should return the same instance on repeated calls."""
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2

    def test_settings_default_values(self, settings: Settings) -> None:
        """Default settings should be populated with expected values."""
        assert settings.application.name == "EV-DDSS"
        assert settings.application.version == "0.1.0"
        assert settings.application.port == 8000
        assert settings.database.pool_size == 10
        assert settings.qdrant.timeout == 30
        assert settings.embedding.dimension == 1536

    def test_application_settings(self, settings: Settings) -> None:
        """Application sub-settings should be properly typed."""
        assert isinstance(settings.application.host, str)
        assert isinstance(settings.application.port, int)
        assert isinstance(settings.application.debug, bool)

    def test_logging_settings(self, settings: Settings) -> None:
        """Logging settings should have sensible defaults."""
        assert settings.logging.console is True
        assert settings.logging.file is True
        assert settings.logging.rotation == "10 MB"
        assert "logs/" in settings.logging.file_path

    def test_database_settings(self, settings: Settings) -> None:
        """Database settings should include pool configuration."""
        assert settings.database.pool_pre_ping is True
        assert "postgresql" in settings.database.url

    def test_qdrant_settings(self, settings: Settings) -> None:
        """Qdrant settings should include URL and timeout."""
        assert "localhost" in settings.qdrant.url
        assert settings.qdrant.timeout >= 1

    def test_data_settings(self, settings: Settings) -> None:
        """Data path settings should point to ./data/ subdirectories."""
        assert "data/raw" in settings.data.raw
        assert "data/processed" in settings.data.processed
        assert "data/embeddings" in settings.data.embeddings
