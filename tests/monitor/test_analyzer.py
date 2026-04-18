import numpy as np
from monitor.analyzer import VolatilityAnalyzer

def test_volatility_trigger_no_trigger():
    analyzer = VolatilityAnalyzer(threshold_pct=5, std_multiplier=2)
    # 5% 變動但偏離只有 1σ — 不觸發
    triggered, info = analyzer.check_volatility(
        current_price=100.0,
        price_5min_ago=95.24,   # 5% up
        price_24h_ago=100.0,
        rolling_24h_prices=[100.0] * 144
    )
    assert triggered is False

def test_volatility_trigger_with_std():
    analyzer = VolatilityAnalyzer(threshold_pct=5, std_multiplier=2)
    # 5% 變動且偏離 2.5σ — 觸發
    rolling = [100.0] * 100 + [95.0] * 44
    triggered, info = analyzer.check_volatility(
        current_price=105.0,
        price_5min_ago=100.0,  # 5% up
        price_24h_ago=100.0,
        rolling_24h_prices=rolling
    )
    assert triggered is True
    assert info["change_pct"] == 5.0
    assert info["std_devs"] >= 2.0

def test_small_change_no_trigger():
    analyzer = VolatilityAnalyzer(threshold_pct=5, std_multiplier=2)
    triggered, info = analyzer.check_volatility(
        current_price=100.5,
        price_5min_ago=100.0,   # 0.5% up
        price_24h_ago=100.0,
        rolling_24h_prices=[100.0] * 144
    )
    assert triggered is False

def test_zero_price_5min_ago():
    analyzer = VolatilityAnalyzer(threshold_pct=5, std_multiplier=2)
    triggered, info = analyzer.check_volatility(
        current_price=100.0,
        price_5min_ago=0.0,
        price_24h_ago=100.0,
        rolling_24h_prices=[100.0] * 144
    )
    assert triggered is False
    assert "error" in info

def test_zero_prices_in_rolling():
    analyzer = VolatilityAnalyzer(threshold_pct=5, std_multiplier=2)
    triggered, info = analyzer.check_volatility(
        current_price=100.0,
        price_5min_ago=100.0,
        price_24h_ago=100.0,
        rolling_24h_prices=[0.0] * 50 + [100.0] * 94
    )
    # Should not crash, should return no trigger
    assert triggered is False