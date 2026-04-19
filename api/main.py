import asyncio
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from monitor.state import StateManager
import logging

logger = logging.getLogger("binance-monitor-api")

app = FastAPI(title="Binance Monitor API")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
)

_state: StateManager | None = None
_app_state_file = "state.json"


# ---------------------------------------------------------------------------
# SSE Broadcast Manager
# ---------------------------------------------------------------------------
class SSEBroadcaster:
    """Manages SSE client connections and broadcasts events to all clients."""

    def __init__(self):
        self._clients: set[asyncio.Queue] = set()

    async def connect(self) -> asyncio.Queue:
        """Register a new SSE client and return its event queue."""
        queue: asyncio.Queue = asyncio.Queue()
        self._clients.add(queue)
        logger.info(f"SSE client connected (total: {len(self._clients)})")
        return queue

    def disconnect(self, queue: asyncio.Queue):
        """Remove a client on disconnect."""
        self._clients.discard(queue)
        logger.info(f"SSE client disconnected (total: {len(self._clients)})")

    async def broadcast(self, event: str, data: dict):
        """Push an event to all connected clients."""
        if not self._clients:
            return
        message = f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
        # Drain all queues concurrently
        await asyncio.gather(
            *(q.put(message) for q in list(self._clients)),
            return_exceptions=True
        )


_broadcaster = SSEBroadcaster()


# ---------------------------------------------------------------------------
# State access
# ---------------------------------------------------------------------------
def get_state() -> StateManager:
    global _state
    if _state is None:
        _state = StateManager(_app_state_file)
    _state.data = _state._load()
    return _state


# ---------------------------------------------------------------------------
# SSE endpoint
# ---------------------------------------------------------------------------
@app.get("/api/events")
async def sse_events():
    """SSE stream: clients listen here for real-time state updates."""

    async def event_generator():
        queue = await _broadcaster.connect()
        try:
            # Send a connected heartbeat
            yield f"event: connected\ndata: {{}}\n\n"
            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=30)
                    yield message
                except asyncio.TimeoutError:
                    # Keepalive heartbeat
                    yield f": keepalive\n\n"
        finally:
            _broadcaster.disconnect(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/events/broadcast")
async def broadcast_event(event: str = "update", data: dict | None = None):
    """
    Internal endpoint: Monitor calls this after state.save()
    to push an update to all SSE clients.
    """
    payload = data if data is not None else {}
    await _broadcaster.broadcast(event, payload)
    return {"status": "ok", "clients": len(_broadcaster._clients)}


# ---------------------------------------------------------------------------
# REST endpoints
# ---------------------------------------------------------------------------
class VolatilitySettingsUpdate(BaseModel):
    enabled: bool | None = None
    threshold_pct: float | None = None
    std_multiplier: float | None = None
    track_interval_minutes: int | None = None


class FundingRateSettingsUpdate(BaseModel):
    enabled: bool | None = None
    threshold: float | None = None
    track_interval_minutes: int | None = None


@app.get("/api/state")
def get_state_endpoint():
    return get_state().data


@app.get("/api/settings")
def get_settings_endpoint():
    return get_state().data["settings"]


@app.put("/api/settings/volatility")
def update_volatility_settings(settings: VolatilitySettingsUpdate):
    state = get_state()
    update = settings.model_dump(exclude_none=True)
    state.data["settings"]["volatility"].update(update)
    state.save()
    return {"status": "ok", "volatility": state.data["settings"]["volatility"]}


@app.put("/api/settings/funding-rate")
def update_funding_rate_settings(settings: FundingRateSettingsUpdate):
    state = get_state()
    update = settings.model_dump(exclude_none=True)
    state.data["settings"]["funding_rate"].update(update)
    state.save()
    return {"status": "ok", "funding_rate": state.data["settings"]["funding_rate"]}


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
