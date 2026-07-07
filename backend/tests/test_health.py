"""Tests for health endpoints."""

import sys
from pathlib import Path

_ev_ddss = Path(__file__).resolve().parent.parent.parent / "ev-ddss"
if str(_ev_ddss) not in sys.path:
    sys.path.insert(0, str(_ev_ddss))

from app import create_app
from fastapi.testclient import TestClient

client = TestClient(create_app())


def test_root():
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "running"
    assert "version" in data


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"


def test_version():
    resp = client.get("/version")
    assert resp.status_code == 200
    data = resp.json()
    assert "version" in data
    assert "python" in data


def test_docs_redirect():
    resp = client.get("/docs", follow_redirects=False)
    assert resp.status_code in (200, 307, 308)
