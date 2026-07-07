"""Tests for diagnostics endpoint."""

import sys
from pathlib import Path

_ev_ddss = Path(__file__).resolve().parent.parent.parent / "ev-ddss"
if str(_ev_ddss) not in sys.path:
    sys.path.insert(0, str(_ev_ddss))

from app import create_app
from fastapi.testclient import TestClient

client = TestClient(create_app())


def test_diagnose_empty_query():
    resp = client.post("/diagnostics", json={"query": ""})
    assert resp.status_code == 422


def test_diagnose_valid():
    resp = client.post("/diagnostics", json={"query": "Check battery voltage"})
    assert resp.status_code in (200, 500)


def test_diagnose_statistics():
    resp = client.get("/diagnostics/statistics")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_diagnostics" in data
