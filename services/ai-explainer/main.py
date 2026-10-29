import asyncio
import json
import os

import asyncpg
import redis.asyncio as aioredis
from chain import explain_alert
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="AI Explainer Service", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
Instrumentator().instrument(app).expose(app)

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
DSN = "postgresql://{user}:{password}@{host}:{port}/{db}".format(
    user=os.getenv("POSTGRES_USER", "monitor"),
    password=os.getenv("POSTGRES_PASSWORD", "monitor123"),
    host=os.getenv("POSTGRES_HOST", "postgres"),
    port=os.getenv("POSTGRES_PORT", "5432"),
    db=os.getenv("POSTGRES_DB", "monitoring"),
)

_pool: asyncpg.Pool | None = None


async def get_pool():
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(DSN, min_size=1, max_size=5)
    return _pool


@app.get("/health")
def health():
    return {"status": "ok", "service": "ai-explainer"}


@app.get("/explanation/{alert_id}")
async def get_explanation(alert_id: int):
    pool = await get_pool()
    row = await pool.fetchrow("SELECT * FROM alerts WHERE id = $1", alert_id)
    if not row:
        raise HTTPException(status_code=404, detail="Alert not found")

    if row["ai_explanation"]:
        return {"alert_id": alert_id, "explanation": row["ai_explanation"]}

    alert = dict(row)
    explanation = await explain_alert(alert)
    await pool.execute("UPDATE alerts SET ai_explanation = $1 WHERE id = $2", explanation, alert_id)
    return {"alert_id": alert_id, "explanation": explanation}


async def listen_and_explain():
    r = await aioredis.from_url(f"redis://{REDIS_HOST}:{REDIS_PORT}", decode_responses=True)
    pubsub = r.pubsub()
    await pubsub.subscribe("flagged_alerts")
    print("AI explainer listening on flagged_alerts...", flush=True)

    async for message in pubsub.listen():
        if message["type"] != "message":
            continue
        try:
            alert = json.loads(message["data"])
            explanation = await explain_alert(alert)
            pool = await get_pool()
            await pool.execute(
                "UPDATE alerts SET ai_explanation = $1 WHERE transaction_id = $2",
                explanation,
                alert["transaction_id"],
            )
        except Exception as exc:
            print(f"AI explainer error: {exc}", flush=True)


@app.on_event("startup")
async def startup():
    asyncio.create_task(listen_and_explain())
