"""Pytest configuration and shared fixtures for EV-DDSS tests."""

import sys
from pathlib import Path

# Ensure project root is on sys.path
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import pytest
from fastapi.testclient import TestClient

from backend.api.server import create_app
from config import get_settings
from database.connection import get_database
from database.qdrant import get_qdrant


@pytest.fixture(scope="session")
def settings():
    """Provide the application settings singleton."""
    return get_settings(reload=True)


@pytest.fixture(scope="session")
def app():
    """Create the FastAPI application for testing."""
    return create_app()


@pytest.fixture(scope="session")
def client(app):
    """Provide a TestClient for the FastAPI application."""
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def database():
    """Provide the DatabaseManager singleton (connection optional)."""
    return get_database()


@pytest.fixture(scope="session")
def qdrant():
    """Provide the QdrantManager singleton (connection optional)."""
    return get_qdrant()
