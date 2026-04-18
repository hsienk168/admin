#!/usr/bin/env python3
import asyncio
import os
from monitor.state import StateManager
from monitor.notifier import TelegramNotifier
from monitor.trigger import TriggerEngine
from monitor.polling import BinanceMarketMonitor

def main():
    state_file = os.getenv("STATE_FILE", "state.json")
    state = StateManager(state_file)

    # Load config
    config = {}
    if os.path.exists("config.json"):
        import json
        with open("config.json") as f:
            config = json.load(f)

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", config.get("telegram_bot_token", ""))
    chat_id = os.getenv("TELEGRAM_CHAT_ID", config.get("telegram_chat_id", ""))

    if not bot_token or not chat_id:
        print("ERROR: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set")
        return

    notifier = TelegramNotifier(bot_token=bot_token, chat_id=chat_id)
    notifier.send_noop()

    trigger = TriggerEngine(state, notifier)
    monitor = BinanceMarketMonitor(state, trigger)

    print("Binance Monitor started. Press Ctrl+C to stop.")
    try:
        asyncio.run(monitor.start())
    except KeyboardInterrupt:
        print("\nShutting down...")

if __name__ == "__main__":
    main()
