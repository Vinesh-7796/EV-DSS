"""EV-DDSS Backend Package.

Provides core application infrastructure:

    - logger:       Pre-configured Loguru logger
    - create_app:   FastAPI application factory
"""

from backend.api.server import create_app

__all__ = ["create_app"]
