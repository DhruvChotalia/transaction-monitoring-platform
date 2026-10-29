import asyncio
import json
import os
import redis.asyncio as aioredis
from fastapi import WebSocket
from typing import List

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

_connections: List[WebSocket] = []


async def connect(ws: WebSocket):
    await ws.accept()
    _connections.append(ws)


def disconnect(ws: WebSocket):
    if ws in _connections:
        _connections.remove(ws)


async def broadcast(data: dict):
    dead = []
    for ws in _connections:
        try:
            await ws.send_json(data)
        except Exception:
            dead.append(ws)
    for ws in dead:
        disconnect(ws)


async def redis_listener():
    r = await aioredis.from_url(f"redis://{REDIS_HOST}:{REDIS_PORT}", decode_responses=True)
    pubsub = r.pubsub()
    await pubsub.subscribe("live_alerts")
    print("Dashboard API WebSocket relay listening on live_alerts...", flush=True)

    async for message in pubsub.listen():
        if message["type"] != "message":
            continue
        try:
            alert = json.loads(message["data"])
            await broadcast(alert)
        except Exception as exc:
            print(f"WebSocket relay error: {exc}", flush=True)
