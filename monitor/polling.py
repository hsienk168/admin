"""
Binance Market Monitor - REST Polling Implementation

Problem: WebSocket !ticker@arr stream does not receive messages in this environment.
Solution: Poll Binance 24hr ticker REST API every 10 seconds.

全市場現貨交易對（300+），10秒刷新
"""
import asyncio
import logging
import sys
import requests
from datetime import datetime, timezone, timedelta
from collections import deque
from typing import Optional
from .state import StateManager
from .trigger import TriggerEngine
from .notifier import TelegramNotifier

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("binance-monitor")

# API base URL for broadcasting state changes to SSE clients
_API_BASE = "http://localhost:8765"


class BinanceMarketMonitor:
    """Polls Binance for market data and triggers alerts."""

    SPOT_TICKER_URL = "https://api.binance.com/api/v3/ticker/24hr"
    FUTURES_PREMIUM_INDEX_URL = "https://fapi.binance.com/fapi/v1/premiumIndex"

    def __init__(
        self,
        state: StateManager,
        trigger: Optional[TriggerEngine] = None,
        funding_rate_cache: Optional[dict] = None,
    ):
        self.state = state
        self.trigger = trigger
        self.funding_rate_cache: dict = funding_rate_cache or {}
        self._prev_prices: dict = {}   # symbol -> previous price (from last poll)
        self._price_history: dict = {}  # symbol -> deque of (timestamp, price), kept for 5min
        self._poll_count = 0

    @property
    def notifier(self):
        """Delegate to trigger's notifier for backward compatibility."""
        return self.trigger.notifier

    def _broadcast_state(self):
        """Fire-and-forget SSE broadcast after state changes."""
        try:
            import threading
            def _post():
                requests.post(
                    f"{_API_BASE}/api/events/broadcast",
                    json={"tracked_pairs": self.state.data.get("tracked_pairs", {})},
                    timeout=3,
                )
            t = threading.Thread(target=_post, daemon=True)
            t.start()
        except Exception as e:
            logger.warning(f"SSE broadcast failed: {e}")

    async def start(self):
        """Main polling loop."""
        logger.info("Binance Market Monitor started (REST polling mode)")
        # Mark as monitored
        self.state.data["monitored_at"] = datetime.now(timezone.utc).isoformat()
        self.state.save()
        self._broadcast_state()
        while True:
            try:
                self._poll_count += 1
                await self._poll_once()
            except Exception as e:
                logger.error(f"Poll error: {e}")
            await asyncio.sleep(10)  # poll every 10 seconds

    async def _poll_once(self):
        """Fetch and process all market data once."""
        # Reload settings from disk every minute so API updates take effect
        if self._poll_count % 6 == 0:
            self.state.data = self.state._load()
            if self.trigger:
                self.trigger.reload()
        tickers = await self._fetch_spot_tickers()
        if tickers is not None:
            self._process_tickers(tickers)
        await self._fetch_funding_rates()

    async def _fetch_spot_tickers(self) -> Optional[list]:
        """Fetch all spot 24hr tickers from Binance REST API."""
        try:
            resp = requests.get(self.SPOT_TICKER_URL, timeout=15)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            logger.warning(f"Failed to fetch spot tickers: {e}")
        return None

    async def _fetch_funding_rates(self):
        """Fetch funding rates from futures API."""
        vs = self.state.data["settings"]["volatility"]
        fs = self.state.data["settings"]["funding_rate"]
        try:
            resp = requests.get(self.FUTURES_PREMIUM_INDEX_URL, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                for item in data:
                    symbol = item["symbol"]
                    funding_rate = float(item.get("lastFundingRate", 0))
                    self.funding_rate_cache[symbol] = funding_rate
                    if self.trigger:
                        tracked = self.state.data["tracked_pairs"].get(symbol)
                        if tracked and tracked.get("trigger_reason") == "funding_rate":
                            mark_price = float(item.get("markPrice", 0))
                            if mark_price > 0:
                                self.trigger.check_tracking(
                                    symbol, mark_price, fs["track_interval_minutes"]
                                )
                        else:
                            self.trigger.process_funding_rate(symbol, funding_rate)
        except Exception as e:
            logger.warning(f"Failed to fetch funding rates: {e}")

    def _process_tickers(self, tickers: list):
        """
        Process ticker data.
        Use 5-minute price change % as the volatility metric.
        Keep rolling price history per symbol and compute change from ~5min ago.
        """
        if self.trigger is None:
            return

        vs = self.state.data["settings"]["volatility"]
        fs = self.state.data["settings"]["funding_rate"]
        vol_threshold = vs["threshold_pct"]
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(minutes=5)

        for ticker in tickers:
            try:
                symbol = ticker["symbol"]
                last_price = float(ticker["lastPrice"])

                if last_price <= 0:
                    continue

                # Skip non-USDT stablecoin pairs
                if not symbol.endswith("USDT"):
                    continue

                # Update rolling price history (keep last 5 min)
                if symbol not in self._price_history:
                    self._price_history[symbol] = deque(maxlen=60)  # ~10s intervals, 60 = 10min buffer
                self._price_history[symbol].append((now, last_price))

                # Prune old entries
                while self._price_history[symbol] and self._price_history[symbol][0][0] < cutoff:
                    self._price_history[symbol].popleft()

                # Calculate 5-minute change %
                history = self._price_history[symbol]
                price_5min_ago = None
                for ts, price in history:
                    if ts <= cutoff:
                        price_5min_ago = price
                        break

                if price_5min_ago is None or len(history) < 2:
                    # Not enough history yet, skip
                    if symbol in self.state.data["tracked_pairs"]:
                        tracked = self.state.data["tracked_pairs"][symbol]
                        interval = (
                            vs["track_interval_minutes"]
                            if tracked.get("trigger_reason") == "volatility"
                            else fs["track_interval_minutes"]
                        )
                        self.trigger.check_tracking(symbol, last_price, interval)
                    continue

                change_pct_5m = ((last_price - price_5min_ago) / price_5min_ago) * 100

                # Check volatility trigger: 5min change >= threshold
                if abs(change_pct_5m) >= vol_threshold:
                    if symbol not in self.state.data["tracked_pairs"]:
                        next_report = now + timedelta(minutes=vs["track_interval_minutes"])
                        self.state.update_tracked_pair(symbol, {
                            "triggered_at": now.isoformat(),
                            "trigger_reason": "volatility",
                            "trigger_price": last_price,
                            "volatility_pct": round(change_pct_5m, 2),
                            "std_devs": None,
                            "funding_rate": None,
                            "next_report_at": next_report.isoformat(),
                            "report_count": 0
                        })
                        self.state.save()
                        self.notifier.send_volatility_alert(
                            symbol=symbol,
                            price=last_price,
                            change_pct=round(change_pct_5m, 2),
                            std_devs=0
                        )
                        logger.info(f"Volatility triggered: {symbol} {change_pct_5m:+.2f}% (5m)")
                # Check tracked pairs for interval reports
                if symbol in self.state.data["tracked_pairs"]:
                    tracked = self.state.data["tracked_pairs"][symbol]
                    interval = (
                        vs["track_interval_minutes"]
                        if tracked.get("trigger_reason") == "volatility"
                        else fs["track_interval_minutes"]
                    )
                    self.trigger.check_tracking(symbol, last_price, interval)

            except (KeyError, ValueError, TypeError):
                continue

        if self._poll_count % 6 == 0:  # Log every minute (6 x 10s)
            logger.info(f"[{now.isoformat()}] Polled {len(tickers)} symbols, tracked: {len(self.state.data['tracked_pairs'])}")
