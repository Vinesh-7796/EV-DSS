"""Tests for configuration endpoints."""

import sys
from pathlib import Path

_ev_ddss = Path(__file__).resolve().parent.parent.parent / "ev-ddss"
if str(_ev_ddss) not in sys.path:
    sys.path.insert(0, str(_ev_ddss))

from app import create_app
from fastapi.testclient import TestClient

client = TestClient(create_app())


def test_get_config():
    resp = client.get("/config")
    assert resp.status_code == 200
    data = resp.json()
    assert "application" in data
    assert "reasoning" in data


def test_get_statistics():
    resp = client.get("/statistics")
    assert resp.status_code == 200
    data = resp.json()
    assert "documents_processed" in data
