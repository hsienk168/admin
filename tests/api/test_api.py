import pytest
from fastapi.testclient import TestClient
from api.main import app, get_state

def test_get_state():
    state = get_state()
    assert "tracked_pairs" in state.data

def test_get_settings():
    client = TestClient(app)
    resp = client.get("/api/settings")
    assert resp.status_code == 200
    assert "volatility" in resp.json()
    assert "funding_rate" in resp.json()

def test_update_volatility_settings():
    client = TestClient(app)
    resp = client.put("/api/settings/volatility", json={"threshold_pct": 3})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["volatility"]["threshold_pct"] == 3

def test_update_funding_rate_settings():
    client = TestClient(app)
    resp = client.put("/api/settings/funding-rate", json={"threshold": -0.5})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["funding_rate"]["threshold"] == -0.5

def test_toggle_volatility_enabled():
    client = TestClient(app)
    resp = client.put("/api/settings/volatility", json={"enabled": False})
    assert resp.status_code == 200
    assert resp.json()["volatility"]["enabled"] is False

def test_toggle_funding_rate_enabled():
    client = TestClient(app)
    resp = client.put("/api/settings/funding-rate", json={"enabled": False})
    assert resp.status_code == 200
    assert resp.json()["funding_rate"]["enabled"] is False
