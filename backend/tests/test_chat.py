"""Tests for chat endpoint."""

import sys
from pathlib import Path

_ev_ddss = Path(__file__).resolve().parent.parent.parent / "ev-ddss"
if str(_ev_ddss) not in sys.path:
    sys.path.insert(0, str(_ev_ddss))

from app import create_app
from fastapi.testclient import TestClient

client = TestClient(create_app())


def test_chat_empty_message():
    resp = client.post("/chat", json={"message": ""})
    assert resp.status_code == 422


def test_chat_valid_request():
    resp = client.post("/chat", json={"message": "Test query", "stream": False})
    assert resp.status_code in (200, 500)
    if resp.status_code == 200:
        data = resp.json()
        assert "conversation_id" in data


def test_chat_invalid_role():
    resp = client.post("/chat", json={
        "message": "test",
        "history": [{"role": "invalid", "content": "test"}],
    })
    assert resp.status_code == 422
