import asyncio
import json
import websockets
from datetime import datetime, timezone
from typing import Optional
from .state import StateManager
from .trigger import TriggerEngine
from .notifier import TelegramNotifier

class BinanceMonitor:
    def __init__(
        self,
        state: StateManager,
        trigger: Optional[TriggerEngine] = None,
        funding_rate_cache: Optional[dict] = None
    ):
        self.state = state
        self.trigger = trigger
        self.price_cache: dict = {}         # symbol -> current price
        self.price_5min_ago: dict = {}       # symbol -> price 5 min ago
        self.funding_rate_cache: dict = funding_rate_cache or {}
        self._last_5min_check: dict = {}     # symbol -> timestamp
        self._last_reload_time: float = 0    # timestamp for reload throttle

    def _process_ticker(self, msg: dict):
        symbol = msg["s"]
        current_price = float(msg["c"])

        # Update 5-min price if needed (check every 5 minutes)
        now = datetime.now(timezone.utc)
        last_check = self._last_5min_check.get(symbol)
        if last_check is None or (now - last_check).total_seconds() >= 300:
            self.price_5min_ago[symbol] = self.price_cache.get(symbol, current_price)
            self._last_5min_check[symbol] = now

        old_price = self.price_cache.get(symbol)
        self.price_cache[symbol] = current_price

        # Check volatility trigger (only if we have enough history)
        if symbol not in self.state.data["tracked_pairs"] and self.trigger:
            price_5min = self.price_5min_ago.get(symbol, current_price)
            rolling = self.price_cache.get(symbol, [current_price])
            self.trigger.process_volatility(
                symbol=symbol,
                current_price=current_price,
                price_5min_ago=price_5min,
                rolling_24h=[current_price]  # simplified for init
            )

        # Check tracking
        if symbol in self.state.data["tracked_pairs"] and self.trigger:
            tracked = self.state.data["tracked_pairs"].get(symbol)
            if tracked:
                reason = tracked.get("trigger_reason")
                if reason == "volatility":
                    interval = self.state.data["settings"]["volatility"]["track_interval_minutes"]
                else:
                    interval = self.state.data["settings"]["funding_rate"]["track_interval_minutes"]
                self.trigger.check_tracking(symbol, current_price, interval)

    def _check_tracking(self, symbol: str):
        """Check if a tracked symbol needs a tracking report."""
        if symbol not in self.state.data["tracked_pairs"]:
            return
        current_price = self.price_cache.get(symbol)
        if current_price is None:
            return
        if self.trigger:
            tracked = self.state.data["tracked_pairs"].get(symbol)
            if tracked:
                reason = tracked.get("trigger_reason")
                if reason == "volatility":
                    interval = self.state.data["settings"]["volatility"]["track_interval_minutes"]
                else:
                    interval = self.state.data["settings"]["funding_rate"]["track_interval_minutes"]
                self.trigger.check_tracking(symbol, current_price, interval)

    async def _fetch_funding_rates(self):
        """Background task: fetch funding rates from Binance API."""
        import requests
        while True:
            try:
                url = "https://fapi.binance.com/fapi/v1/premiumIndex"
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data:
                        symbol = item["symbol"]
                        funding_rate = float(item.get("lastFundingRate", 0))
                        self.funding_rate_cache[symbol] = funding_rate

                        # Throttle reload to once per minute
                        now_ts = asyncio.get_event_loop().time()
                        if now_ts - self._last_reload_time >= 60:
                            self.state.data = self.state._load()
                            if self.trigger:
                                self.trigger.reload()
                            self._last_reload_time = now_ts

                        fs = self.state.data["settings"]["funding_rate"]
                        if self.trigger and funding_rate < fs["threshold"] / 100:
                            self.trigger.process_funding_rate(symbol, funding_rate)
            except Exception:
                pass
            await asyncio.sleep(60)  # check every minute

    async def start(self):
        """Main WebSocket loop."""
        uri = "wss://stream.binance.com:9443/ws/!ticker@arr"

        async def run():
            async for ws in websockets.connect(uri):
                try:
                    async for msg in ws:
                        data = json.loads(msg)
                        if isinstance(data, list):
                            for ticker in data:
                                if ticker["e"] == "24hrTicker":
                                    self._process_ticker(ticker)
                        elif data.get("e") == "24hrTicker":
                            self._process_ticker(data)
                except websockets.ConnectionClosed:
                    continue

        await asyncio.gather(run(), self._fetch_funding_rates())


async def main():
    state = StateManager("state.json")
    notifier = TelegramNotifier(
        bot_token=state.data.get("bot_token", ""),
        chat_id=state.data.get("chat_id", "")
    )
    trigger = TriggerEngine(state, notifier)
    monitor = BinanceMonitor(state, trigger)
    await monitor.start()

if __name__ == "__main__":
    asyncio.run(main())
