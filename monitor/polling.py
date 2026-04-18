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
        self._poll_count = 0

    @property
    def notifier(self):
        """Delegate to trigger's notifier for backward compatibility."""
        return self.trigger.notifier

    async def start(self):
        """Main polling loop."""
        logger.info("Binance Market Monitor started (REST polling mode)")
        # Mark as monitored
        self.state.data["monitored_at"] = datetime.now(timezone.utc).isoformat()
        self.state.save()
        while True:
            try:
                self._poll_count += 1
                await self._poll_once()
            except Exception as e:
                logger.error(f"Poll error: {e}")
            await asyncio.sleep(10)  # poll every 10 seconds

    async def _poll_once(self):
        """Fetch and process all market data once."""
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
        try:
            resp = requests.get(self.FUTURES_PREMIUM_INDEX_URL, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                for item in data:
                    symbol = item["symbol"]
                    # lastFundingRate is already in decimal form (e.g., -0.0001 = -0.01%)
                    # Compare directly with threshold (e.g., -0.01 = -1%)
                    funding_rate = float(item.get("lastFundingRate", 0))
                    self.funding_rate_cache[symbol] = funding_rate
                    if self.trigger and funding_rate < self.state.data["settings"]["funding_rate_threshold"]:
                        self.trigger.process_funding_rate(symbol, funding_rate)
        except Exception as e:
            logger.warning(f"Failed to fetch funding rates: {e}")

    def _process_tickers(self, tickers: list):
        """
        Process 24hr ticker data.
        Use Binance's priceChangePercent (24h change) as the volatility metric.
        Trigger if 24h change >= volatility_threshold_pct.
        """
        if self.trigger is None:
            return

        settings = self.state.data["settings"]
        vol_threshold = settings["volatility_threshold_pct"]

        for ticker in tickers:
            try:
                symbol = ticker["symbol"]
                last_price = float(ticker["lastPrice"])

                if last_price <= 0:
                    continue

                # Skip non-USDT stablecoin pairs
                if not symbol.endswith("USDT"):
                    continue

                # Use 24h price change % as volatility metric
                price_change_pct = float(ticker.get("priceChangePercent", 0))

                # Check volatility trigger: 24h change >= threshold
                # Bypass VolatilityAnalyzer since we already have 24h change %
                if abs(price_change_pct) >= vol_threshold:
                    if symbol not in self.state.data["tracked_pairs"]:
                        track_interval = self.state.data["settings"]["track_interval_minutes"]
                        next_report = datetime.now(timezone.utc) + timedelta(minutes=track_interval)
                        self.state.update_tracked_pair(symbol, {
                            "triggered_at": datetime.now(timezone.utc).isoformat(),
                            "trigger_reason": "volatility",
                            "trigger_price": last_price,
                            "volatility_pct": round(price_change_pct, 2),
                            "std_devs": None,
                            "funding_rate": None,
                            "next_report_at": next_report.isoformat(),
                            "report_count": 0
                        })
                        self.state.save()
                        self.notifier.send_volatility_alert(
                            symbol=symbol,
                            price=last_price,
                            change_pct=round(price_change_pct, 2),
                            std_devs=0
                        )
                        logger.info(f"Volatility triggered: {symbol} {price_change_pct:+.2f}%")
                # Check tracked pairs for 30-min reports
                if symbol in self.state.data["tracked_pairs"]:
                    self.trigger.check_tracking(symbol, last_price)

            except (KeyError, ValueError, TypeError):
                continue

        if self._poll_count % 6 == 0:  # Log every minute (6 x 10s)
            now = datetime.now(timezone.utc)
            logger.info(f"[{now.isoformat()}] Polled {len(tickers)} symbols, tracked: {len(self.state.data['tracked_pairs'])}")
