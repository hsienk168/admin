from unittest.mock import MagicMock, patch
from monitor.trigger import TriggerEngine

def test_immediate_trigger_volatility():
    state = MagicMock()
    state.data = {
        "settings": {"volatility_threshold_pct": 5, "volatility_std_multiplier": 2, "track_interval_minutes": 30, "funding_rate_threshold": -0.01},
        "tracked_pairs": {}
    }
    notifier = MagicMock()
    engine = TriggerEngine(state, notifier)
    engine.volatility_analyzer.check_volatility = MagicMock(
        return_value=(True, {"change_pct": 5.5, "std_devs": 2.5})
    )
    result = engine.process_volatility(
        symbol="BTCUSDT",
        current_price=105500.0,
        price_5min_ago=100000.0,
        rolling_24h=[100000.0] * 144
    )
    assert result is True
    state.update_tracked_pair.assert_called_once()
    notifier.send_volatility_alert.assert_called_once()

def test_funding_rate_trigger():
    state = MagicMock()
    state.data = {
        "settings": {"volatility_threshold_pct": 5, "volatility_std_multiplier": 2, "track_interval_minutes": 30, "funding_rate_threshold": -0.01},
        "tracked_pairs": {}
    }
    notifier = MagicMock()
    engine = TriggerEngine(state, notifier)
    engine.funding_checker.check = MagicMock(return_value=(True, {"funding_rate": -0.015}))
    result = engine.process_funding_rate(symbol="ETHUSDT", funding_rate=-0.015)
    assert result is True
    state.update_tracked_pair.assert_called_once()
    notifier.send_funding_rate_alert.assert_called_once()

def test_no_double_trigger_same_symbol():
    state = MagicMock()
    state.data = {
        "settings": {"volatility_threshold_pct": 5, "volatility_std_multiplier": 2, "track_interval_minutes": 30, "funding_rate_threshold": -0.01},
        "tracked_pairs": {"BTCUSDT": {"triggered_at": "2026-04-18T10:00:00Z", "next_report_at": None}}
    }
    notifier = MagicMock()
    engine = TriggerEngine(state, notifier)
    engine.volatility_analyzer.check_volatility = MagicMock(return_value=(True, {"change_pct": 5.5, "std_devs": 2.5}))
    result = engine.process_volatility("BTCUSDT", 105500.0, 100000.0, [100000.0] * 144)
    assert state.update_tracked_pair.call_count == 0  # no double notification