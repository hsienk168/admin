import json
import threading
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

class StateManager:
    def __init__(self, state_file: str = "state.json"):
        self.state_file = Path(state_file)
        self._lock = threading.Lock()
        self.data = self._load()

    def _load(self) -> dict:
        if not self.state_file.exists():
            return self._default_state()
        with open(self.state_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def _default_state(self) -> dict:
        return {
            "monitored_at": None,
            "tracked_pairs": {},
            "settings": {
                "volatility_threshold_pct": 5,
                "volatility_std_multiplier": 2,
                "funding_rate_threshold": -0.01,
                "track_interval_minutes": 30
            },
            "alert_history": []
        }

    def save(self):
        with self._lock:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)

    def update_tracked_pair(self, symbol: str, info: dict):
        with self._lock:
            self.data["tracked_pairs"][symbol] = info

    def remove_tracked_pair(self, symbol: str):
        with self._lock:
            if symbol in self.data["tracked_pairs"]:
                del self.data["tracked_pairs"][symbol]

    def update_settings(self, settings: dict):
        with self._lock:
            self.data["settings"].update(settings)

    def add_alert(self, alert: dict):
        with self._lock:
            self.data.setdefault("alert_history", []).insert(0, alert)
            # keep last 100 alerts
            self.data["alert_history"] = self.data["alert_history"][:100]