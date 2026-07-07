"""Enterprise logging module for EV-DDSS.

Provides a configured Loguru logger that writes to console and
rotating log files. All application modules should import this logger:

    from backend.logger import logger
"""

import sys
from pathlib import Path
from typing import Optional

from loguru import logger as _base_logger

from config import get_settings


def setup_logger(log_level: Optional[str] = None) -> None:
    """Configure the application logger.

    Removes the default Loguru handler and adds console and file handlers
    based on the application settings.

    Args:
        log_level: Override the log level. Uses settings if not provided.
    """
    settings = get_settings()
    level = (log_level or settings.application.log_level).upper()

    # Remove default handler
    _base_logger.remove()

    # Console handler
    if settings.logging.console:
        _base_logger.add(
            sys.stderr,
            level=level,
            format=settings.logging.format,
            colorize=True,
            backtrace=settings.application.debug,
            diagnose=settings.application.debug,
        )

    # File handler with rotation
    if settings.logging.file:
        log_path = Path(settings.logging.file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        _base_logger.add(
            str(log_path),
            level=level,
            format=settings.logging.format,
            rotation=settings.logging.rotation,
            retention=settings.logging.retention,
            compression="zip",
            backtrace=settings.application.debug,
            diagnose=settings.application.debug,
            encoding="utf-8",
        )


# Pre-configured logger instance for application-wide use
logger = _base_logger
"""Application-wide logger instance.

Usage:
    from backend.logger import logger
    logger.info("Application started")
    logger.error("Connection failed: {}", error)
"""
