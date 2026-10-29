import asyncio
import json
import os
import httpx
import redis.asyncio as aioredis
from rules import evaluate

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
ML_SCORER_URL = os.getenv("ML_SCORER_URL", "http://ml-scorer:8003")

FRAUD_THRESHOLD = float(os.getenv("FRAUD_THRESHOLD", "0.60"))


async def process(txn: dict, redis_client: aioredis.Redis) -> None:
    rule_flags = evaluate(txn)

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(f"{ML_SCORER_URL}/score", json=txn, timeout=3)
            fraud_prob = resp.json().get("fraud_probability", 0.0)
        except Exception:
            fraud_prob = 0.0

    should_flag = fraud_prob >= FRAUD_THRESHOLD or any(
        f in rule_flags for f in ("high_amount", "very_high_amount", "late_night_high_risk")
    )

    if should_flag:
        alert = {**txn, "fraud_probability": fraud_prob, "rule_flags": rule_flags}
        await redis_client.publish("flagged_alerts", json.dumps(alert))


async def main() -> None:
    r = await aioredis.from_url(f"redis://{REDIS_HOST}:{REDIS_PORT}", decode_responses=True)
    pubsub = r.pubsub()
    await pubsub.subscribe("raw_transactions")
    print("Rules engine listening on raw_transactions...", flush=True)

    async for message in pubsub.listen():
        if message["type"] != "message":
            continue
        try:
            txn = json.loads(message["data"])
            await process(txn, r)
        except Exception as exc:
            print(f"Rules engine error: {exc}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
