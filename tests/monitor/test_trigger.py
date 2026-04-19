from unittest.mock import MagicMock, patch
from monitor.trigger import TriggerEngine

def test_immediate_trigger_volatility():
    state = MagicMock()
    state.data = {
        "settings": {"volatility_threshold_pct": 5, "volatility_std_multiplier": 2, "track_interval_minutes": 30, "funding_rate_threshold": -1.0},
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
        "settings": {"volatility_threshold_pct": 5, "volatility_std_multiplier": 2, "track_interval_minutes": 30, "funding_rate_threshold": -1.0},
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
        "settings": {"volatility_threshold_pct": 5, "volatility_std_multiplier": 2, "track_interval_minutes": 30, "funding_rate_threshold": -1.0},
        "tracked_pairs": {"BTCUSDT": {"triggered_at": "2026-04-18T10:00:00Z", "next_report_at": None}}
    }
    notifier = MagicMock()
    engine = TriggerEngine(state, notifier)
    engine.volatility_analyzer.check_volatility = MagicMock(return_value=(True, {"change_pct": 5.5, "std_devs": 2.5}))
    result = engine.process_volatility("BTCUSDT", 105500.0, 100000.0, [100000.0] * 144)
    assert state.update_tracked_pair.call_count == 0  # no double notification


def test_reload_updates_tracked_pairs_next_report_at():
    """reload() should reschedule all tracked pairs with the new track_interval_minutes."""
    from datetime import datetime, timezone, timedelta

    old_interval = 30
    new_interval = 10
    now = datetime.now(timezone.utc)

    state = MagicMock()
    state.data = {
        "settings": {
            "volatility_threshold_pct": 5,
            "volatility_std_multiplier": 2,
            "track_interval_minutes": old_interval,
            "funding_rate_threshold": -1.0,
        },
        "tracked_pairs": {
            "BTCUSDT": {
                "triggered_at": "2026-04-18T10:00:00+00:00",
                "trigger_reason": "volatility",
                "trigger_price": 100000.0,
                "volatility_pct": 10.0,
                "std_devs": None,
                "funding_rate": None,
                "next_report_at": (now + timedelta(minutes=old_interval)).isoformat(),
                "report_count": 2,
            },
            "ETHUSDT": {
                "triggered_at": "2026-04-18T10:05:00+00:00",
                "trigger_reason": "funding_rate",
                "trigger_price": None,
                "volatility_pct": None,
                "std_devs": None,
                "funding_rate": -0.02,
                "next_report_at": (now + timedelta(minutes=old_interval)).isoformat(),
                "report_count": 1,
            },
        },
    }

    notifier = MagicMock()
    engine = TriggerEngine(state, notifier)

    # Simulate API updating track_interval_minutes to new_interval
    state.data["settings"]["track_interval_minutes"] = new_interval

    # reload() should update tracked pairs
    engine.reload()

    # Verify state.update_tracked_pair was called for each tracked pair
    assert state.update_tracked_pair.call_count == 2

    # Collect all calls
    calls = state.update_tracked_pair.call_args_list

    # Verify both tracked pairs got rescheduled with new_interval
    updated_symbols = set()
    for call in calls:
        symbol, info = call[0]
        updated_symbols.add(symbol)
        # next_report_at should be within new_interval minutes from now
        next_report = datetime.fromisoformat(info["next_report_at"].replace("Z", "+00:00"))
        # Allow 2-second tolerance for test execution time
        expected_min = now + timedelta(minutes=new_interval - 0, seconds=-2)
        expected_max = now + timedelta(minutes=new_interval, seconds=2)
        assert expected_min <= next_report <= expected_max, \
            f"{symbol}: next_report_at={next_report} not within [{expected_min}, {expected_max}]"

    assert updated_symbols == {"BTCUSDT", "ETHUSDT"}


def test_reload_clears_tracked_pairs_below_new_volatility_threshold():
    """
    When volatility_threshold_pct is increased, any tracked pair whose
    volatility_pct is below the new threshold should be removed.
    """
    state = MagicMock()
    state.data = {
        "settings": {
            "volatility_threshold_pct": 10,
            "volatility_std_multiplier": 2,
            "track_interval_minutes": 30,
            "funding_rate_threshold": -1.0,
        },
        "tracked_pairs": {
            # WAVES: 11.97% — above old 10% threshold, below new 30% threshold → should be removed
            "WAVESUSDT": {
                "triggered_at": "2026-04-18T13:07:49+00:00",
                "trigger_reason": "volatility",
                "trigger_price": 1.076,
                "volatility_pct": 11.97,
                "std_devs": None,
                "funding_rate": None,
                "next_report_at": "2026-04-18T14:00:00+00:00",
                "report_count": 28,
            },
            # BTC: 30% — exactly at new threshold → should be kept
            "BTCUSDT": {
                "triggered_at": "2026-04-18T13:00:00+00:00",
                "trigger_reason": "volatility",
                "trigger_price": 76000.0,
                "volatility_pct": 30.0,
                "std_devs": None,
                "funding_rate": None,
                "next_report_at": "2026-04-18T14:00:00+00:00",
                "report_count": 5,
            },
            # ETH: 50% — above new threshold → should be kept
            "ETHUSDT": {
                "triggered_at": "2026-04-18T13:00:00+00:00",
                "trigger_reason": "volatility",
                "trigger_price": 3000.0,
                "volatility_pct": 50.0,
                "std_devs": None,
                "funding_rate": None,
                "next_report_at": "2026-04-18T14:00:00+00:00",
                "report_count": 3,
            },
            # BNB: triggered by funding_rate (negative), not volatility → should be kept regardless
            "BNBUSDT": {
                "triggered_at": "2026-04-18T13:00:00+00:00",
                "trigger_reason": "funding_rate",
                "trigger_price": None,
                "volatility_pct": None,
                "std_devs": None,
                "funding_rate": -0.025,
                "next_report_at": "2026-04-18T14:00:00+00:00",
                "report_count": 3,
            },
        },
    }

    notifier = MagicMock()
    engine = TriggerEngine(state, notifier)

    # Simulate API updating threshold from 10% to 30%
    state.data["settings"]["volatility_threshold_pct"] = 30

    engine.reload()

    # WAVESUSDT (11.97%) is below new 30% threshold → should be removed
    # BTCUSDT (30%) is exactly at threshold → kept
    # ETHUSDT (50%) is above threshold → kept
    # BNBUSDT (funding_rate, not volatility) → kept regardless
    removed_calls = [call for call in state.remove_tracked_pair.call_args_list]
    assert len(removed_calls) == 1, f"Expected 1 removal, got {len(removed_calls)}: {removed_calls}"
    assert removed_calls[0][0][0] == "WAVESUSDT"

    # BTCUSDT, ETHUSDT, BNBUSDT should remain in tracked_pairs
    remaining = set(state.update_tracked_pair.call_args_list[-1][0][0].split(',')) if state.update_tracked_pair.call_count > 0 else set()
    # More reliable: check that remove was only called once
    assert state.remove_tracked_pair.call_count == 1