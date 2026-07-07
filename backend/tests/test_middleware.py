"""Tests for middleware behavior."""

import sys
from pathlib import Path

_ev_ddss = Path(__file__).resolve().parent.parent.parent / "ev-ddss"
if str(_ev_ddss) not in sys.path:
    sys.path.insert(0, str(_ev_ddss))

from app import create_app
from fastapi.testclient import TestClient

client = TestClient(create_app())


def test_request_id_header():
    resp = client.get("/health", headers={"X-Request-ID": "test-123"})
    assert resp.headers.get("X-Request-ID") == "test-123"


def test_cors_headers():
    resp = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert "access-control-allow-origin" in resp.headers
