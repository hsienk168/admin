import asyncio
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from monitor.state import StateManager

app = FastAPI(title="Binance Monitor API")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
)

_state: StateManager | None = None
_app_state_file = "state.json"

def get_state() -> StateManager:
    global _state
    if _state is None:
        _state = StateManager(_app_state_file)
    # Reload from disk on every request so we see Monitor Agent's updates
    _state.data = _state._load()
    return _state

class SettingsUpdate(BaseModel):
    volatility_threshold_pct: float | None = None
    volatility_std_multiplier: float | None = None
    funding_rate_threshold: float | None = None
    track_interval_minutes: int | None = None

@app.get("/api/state")
def get_state_endpoint():
    return get_state().data

@app.get("/api/settings")
def get_settings_endpoint():
    return get_state().data["settings"]

@app.put("/api/settings")
def update_settings_endpoint(settings: SettingsUpdate):
    state = get_state()
    update = settings.model_dump(exclude_none=True)
    state.update_settings(update)
    state.save()
    return {"status": "ok", "settings": state.data["settings"]}

@app.post("/api/track/{symbol}/stop")
def stop_track_endpoint(symbol: str):
    state = get_state()
    if symbol not in state.data["tracked_pairs"]:
        raise HTTPException(status_code=404, detail="Symbol not tracked")
    state.remove_tracked_pair(symbol)
    state.save()
    return {"status": "ok", "symbol": symbol}

@app.get("/api/health")
def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)