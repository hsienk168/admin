import asyncio
from unittest.mock import MagicMock, patch
from monitor.websocket import BinanceMonitor

def test_process_ticker_updates_price_cache():
    monitor = BinanceMonitor(state=MagicMock(), trigger=MagicMock())
    monitor.price_cache = {"BTCUSDT": 100000.0, "ETHUSDT": 3000.0}

    msg = {
        "e": "24hrTicker",
        "s": "BTCUSDT",
        "c": "105000.0",
        "p": "5000.0",
        "P": "5.0"
    }
    monitor._process_ticker(msg)

    assert monitor.price_cache["BTCUSDT"] == 105000.0
    assert monitor.price_5min_ago["BTCUSDT"] == 100000.0  # old price moved to 5min

def test_tracked_symbol_checked_for_tracking():
    state = MagicMock()
    state.data = {"tracked_pairs": {"BTCUSDT": {
        "triggered_at": "2026-04-18T10:00:00Z",
        "trigger_price": 100000.0,
        "funding_rate": None,
        "volatility_pct": 5.5,
        "next_report_at": "2026-04-18T09:55:00Z",  # past due
        "report_count": 1
    }}, "settings": {}}
    trigger = MagicMock()
    monitor = BinanceMonitor(state=state, trigger=trigger)
    monitor.price_cache = {"BTCUSDT": 105000.0}
    monitor._check_tracking("BTCUSDT")
    trigger.check_tracking.assert_called_once()