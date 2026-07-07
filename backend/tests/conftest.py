"""Shared fixtures for backend Application Layer tests."""

import sys
from pathlib import Path

_ev_ddss = Path(__file__).resolve().parent.parent.parent / "ev-ddss"
if str(_ev_ddss) not in sys.path:
    sys.path.insert(0, str(_ev_ddss))

import pytest
from fastapi.testclient import TestClient

from app import create_app


@pytest.fixture
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c
