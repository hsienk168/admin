import pytest
from httpx import AsyncClient, ASGITransport
from api.main import app, get_state

def test_get_state():
    state = get_state()
    assert "tracked_pairs" in state.data

def test_get_settings():
    from fastapi.testclient import TestClient
    client = TestClient(app)
    resp = client.get("/api/settings")
    assert resp.status_code == 200
    assert "volatility_threshold_pct" in resp.json()

def test_update_settings():
    from fastapi.testclient import TestClient
    client = TestClient(app)
    resp = client.put("/api/settings", json={"volatility_threshold_pct": 3})
    assert resp.status_code == 200