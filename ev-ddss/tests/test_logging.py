"""Tests for the logging module."""

import pytest
from loguru import logger as loguru_logger

from backend.logger import setup_logger


class TestLogging:
    """Verify logging configuration."""

    def test_logger_importable(self) -> None:
        """The logger should be importable from the backend package."""
        from backend.logger import logger
        assert logger is not None

    def test_logger_is_loguru_instance(self) -> None:
        """The logger should be the Loguru base logger."""
        from backend.logger import logger
        assert logger is loguru_logger

    def test_setup_logger_does_not_raise(self) -> None:
        """setup_logger should complete without error."""
        setup_logger("DEBUG")  # Should not raise

    def test_logger_levels(self) -> None:
        """All standard log levels should work."""
        setup_logger("DEBUG")
        loguru_logger.debug("debug test")
        loguru_logger.info("info test")
        loguru_logger.warning("warning test")
        # error would print to stderr but shouldn't raise
        loguru_logger.error("error test")
