import asyncio

from db import (
    fetch_alerts,
    fetch_category_breakdown,
    fetch_hourly_distribution,
    fetch_rules,
    fetch_stats,
)
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from ws import connect, disconnect, redis_listener

app = FastAPI(title="Dashboard API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
Instrumentator().instrument(app).expose(app)

_bg_task = None


@app.on_event("startup")
async def startup():
    global _bg_task
    _bg_task = asyncio.ensure_future(redis_listener())


@app.get("/health")
def health():
    return {"status": "ok", "service": "dashboard-api"}


@app.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    await connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        disconnect(websocket)


@app.get("/alerts")
async def get_alerts(limit: int = 50, offset: int = 0):
    alerts = await fetch_alerts(limit, offset)
    for a in alerts:
        if a.get("created_at"):
            a["created_at"] = a["created_at"].isoformat()
    return alerts


@app.get("/stats")
async def get_stats():
    return await fetch_stats()


@app.get("/analytics/hourly")
async def get_hourly():
    return await fetch_hourly_distribution()


@app.get("/analytics/categories")
async def get_categories():
    return await fetch_category_breakdown()


@app.get("/rules")
async def get_rules():
    rules = await fetch_rules()
    for r in rules:
        if r.get("created_at"):
            r["created_at"] = r["created_at"].isoformat()
    return rules
