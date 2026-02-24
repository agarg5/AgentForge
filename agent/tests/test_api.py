"""Tests for the FastAPI /chat and /health endpoints."""

import pytest
from fastapi.testclient import TestClient

from src.main import app


def test_health():
    with TestClient(app) as tc:
        resp = tc.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_chat_missing_auth():
    with TestClient(app) as tc:
        resp = tc.post("/chat", json={"message": "hello"})
    # FastAPI returns 422 when required header is missing
    assert resp.status_code == 422


def test_chat_empty_bearer():
    with TestClient(app) as tc:
        resp = tc.post(
            "/chat",
            json={"message": "hello"},
            headers={"Authorization": "Bearer "},
        )
    assert resp.status_code == 401
