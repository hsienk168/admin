import json
import tempfile
import os
from monitor.state import StateManager

def test_load_returns_default_state():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write('{"tracked_pairs": {}, "settings": {}, "alert_history": []}')
        tmp = f.name
    try:
        sm = StateManager(tmp)
        assert sm.data == {"tracked_pairs": {}, "settings": {}, "alert_history": []}
    finally:
        os.unlink(tmp)

def test_update_tracked_pair():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write('{"tracked_pairs": {}, "settings": {}, "alert_history": []}')
        tmp = f.name
    try:
        sm = StateManager(tmp)
        sm.update_tracked_pair("BTCUSDT", {"triggered_at": "2026-04-18T10:00:00Z", "trigger_reason": "volatility"})
        assert "BTCUSDT" in sm.data["tracked_pairs"]
    finally:
        os.unlink(tmp)

def test_update_volatility_settings():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write('{"tracked_pairs": {}, "settings": {}, "alert_history": []}')
        tmp = f.name
    try:
        sm = StateManager(tmp)
        sm.data["settings"]["volatility"] = {"enabled": True, "threshold_pct": 5, "std_multiplier": 2, "track_interval_minutes": 30}
        sm.data["settings"]["funding_rate"] = {"enabled": True, "threshold": -1.0, "track_interval_minutes": 30}
        sm.data["settings"]["volatility"]["threshold_pct"] = 3
        sm.save()
        content = json.load(open(tmp))
        assert content["settings"]["volatility"]["threshold_pct"] == 3
    finally:
        os.unlink(tmp)

def test_remove_tracked_pair():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write('{"tracked_pairs": {"BTCUSDT": {}}, "settings": {}, "alert_history": []}')
        tmp = f.name
    try:
        sm = StateManager(tmp)
        assert "BTCUSDT" in sm.data["tracked_pairs"]
        sm.remove_tracked_pair("BTCUSDT")
        assert "BTCUSDT" not in sm.data["tracked_pairs"]
    finally:
        os.unlink(tmp)

def test_remove_tracked_pair_not_found():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write('{"tracked_pairs": {}, "settings": {}, "alert_history": []}')
        tmp = f.name
    try:
        sm = StateManager(tmp)
        sm.remove_tracked_pair("NONEXISTENT")  # should not crash
        assert "NONEXISTENT" not in sm.data["tracked_pairs"]
    finally:
        os.unlink(tmp)

def test_add_alert():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write('{"tracked_pairs": {}, "settings": {}, "alert_history": []}')
        tmp = f.name
    try:
        sm = StateManager(tmp)
        for i in range(105):
            sm.add_alert({"id": i, "msg": f"alert-{i}"})
        # should keep only last 100
        assert len(sm.data["alert_history"]) == 100
        assert sm.data["alert_history"][0]["id"] == 104  # most recent first
    finally:
        os.unlink(tmp)
