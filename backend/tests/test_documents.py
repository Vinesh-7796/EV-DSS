"""Tests for document endpoints."""

import sys
from pathlib import Path

_ev_ddss = Path(__file__).resolve().parent.parent.parent / "ev-ddss"
if str(_ev_ddss) not in sys.path:
    sys.path.insert(0, str(_ev_ddss))

from app import create_app
from fastapi.testclient import TestClient

client = TestClient(create_app())


def test_list_documents():
    resp = client.get("/documents")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_get_document_not_found():
    resp = client.get("/documents/nonexistent")
    assert resp.status_code == 404
