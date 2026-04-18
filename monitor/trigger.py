from datetime import datetime, timezone, timedelta
from typing import Optional
from .analyzer import VolatilityAnalyzer, FundingRateChecker
from .notifier import TelegramNotifier
from .state import StateManager

class TriggerEngine:
    def __init__(self, state: StateManager, notifier: TelegramNotifier):
        self.state = state
        self.notifier = notifier
        self.volatility_analyzer = VolatilityAnalyzer(
            threshold_pct=state.data["settings"]["volatility_threshold_pct"],
            std_multiplier=state.data["settings"]["volatility_std_multiplier"]
        )
        self.funding_checker = FundingRateChecker(
            threshold=state.data["settings"]["funding_rate_threshold"]
        )

    def process_volatility(
        self,
        symbol: str,
        current_price: float,
        price_5min_ago: float,
        rolling_24h: list
    ) -> bool:
        if symbol in self.state.data["tracked_pairs"]:
            return False
        triggered, info = self.volatility_analyzer.check_volatility(
            current_price=current_price,
            price_5min_ago=price_5min_ago,
            price_24h_ago=rolling_24h[0] if rolling_24h else current_price,
            rolling_24h_prices=rolling_24h
        )
        if not triggered:
            return False
        track_interval = self.state.data["settings"]["track_interval_minutes"]
        next_report = datetime.now(timezone.utc) + timedelta(minutes=track_interval)
        self.state.update_tracked_pair(symbol, {
            "triggered_at": datetime.now(timezone.utc).isoformat(),
            "trigger_reason": "volatility",
            "trigger_price": current_price,
            "volatility_pct": info["change_pct"],
            "std_devs": info["std_devs"],
            "funding_rate": None,
            "next_report_at": next_report.isoformat(),
            "report_count": 0
        })
        self.state.save()
        self.notifier.send_volatility_alert(
            symbol=symbol,
            price=current_price,
            change_pct=info["change_pct"],
            std_devs=info["std_devs"]
        )
        return True

    def process_volatility_24h(self, symbol: str, current_price: float, change_pct_24h: float) -> bool:
        """
        Simplified volatility trigger for REST polling mode.
        Uses Binance's 24h priceChangePercent directly.
        change_pct_24h: already a percentage number, e.g. 5.0 for 5% gain.
        """
        if symbol in self.state.data["tracked_pairs"]:
            return False

        vol_threshold = self.state.data["settings"]["volatility_threshold_pct"]
        if abs(change_pct_24h) < vol_threshold:
            return False

        track_interval = self.state.data["settings"]["track_interval_minutes"]
        next_report = datetime.now(timezone.utc) + timedelta(minutes=track_interval)
        self.state.update_tracked_pair(symbol, {
            "triggered_at": datetime.now(timezone.utc).isoformat(),
            "trigger_reason": "volatility",
            "trigger_price": current_price,
            "volatility_pct": change_pct_24h,
            "std_devs": None,
            "funding_rate": None,
            "next_report_at": next_report.isoformat(),
            "report_count": 0
        })
        self.state.save()
        self.notifier.send_volatility_alert(
            symbol=symbol,
            price=current_price,
            change_pct=change_pct_24h,
            std_devs=None
        )
        return True

    def process_funding_rate(self, symbol: str, funding_rate: float) -> bool:
        if symbol in self.state.data["tracked_pairs"]:
            return False
        triggered, info = self.funding_checker.check(funding_rate)
        if not triggered:
            return False
        track_interval = self.state.data["settings"]["track_interval_minutes"]
        next_report = datetime.now(timezone.utc) + timedelta(minutes=track_interval)
        self.state.update_tracked_pair(symbol, {
            "triggered_at": datetime.now(timezone.utc).isoformat(),
            "trigger_reason": "funding_rate",
            "trigger_price": None,
            "volatility_pct": None,
            "std_devs": None,
            "funding_rate": funding_rate,
            "next_report_at": next_report.isoformat(),
            "report_count": 0
        })
        self.state.save()
        self.notifier.send_funding_rate_alert(symbol=symbol, funding_rate=funding_rate)
        return True

    def check_tracking(self, symbol: str, current_price: float) -> bool:
        tracked = self.state.data["tracked_pairs"].get(symbol)
        if not tracked:
            return False
        next_report_at = datetime.fromisoformat(tracked["next_report_at"].replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        if now < next_report_at:
            return False
        trigger_price = tracked.get("trigger_price") or current_price
        change_pct = ((current_price - trigger_price) / trigger_price) * 100 if trigger_price else 0
        new_count = tracked["report_count"] + 1
        track_interval = self.state.data["settings"]["track_interval_minutes"]
        next_report = now + timedelta(minutes=track_interval)
        self.state.update_tracked_pair(symbol, {
            **tracked,
            "next_report_at": next_report.isoformat(),
            "report_count": new_count
        })
        self.state.save()
        self.notifier.send_tracking_report(
            symbol=symbol,
            price=current_price,
            change_pct=change_pct,
            report_count=new_count
        )
        return True

    def stop_tracking(self, symbol: str):
        self.state.remove_tracked_pair(symbol)
        self.state.save()