import asyncio
import json
import os
import redis.asyncio as aioredis
from db import insert_alert

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))


async def main() -> None:
    r = await aioredis.from_url(f"redis://{REDIS_HOST}:{REDIS_PORT}", decode_responses=True)
    pubsub = r.pubsub()
    await pubsub.subscribe("flagged_alerts")
    print("Alert service listening on flagged_alerts...", flush=True)

    async for message in pubsub.listen():
        if message["type"] != "message":
            continue
        try:
            alert = json.loads(message["data"])
            alert_id = await insert_alert(alert)
            if alert_id > 0:
                alert["id"] = alert_id
                await r.publish("live_alerts", json.dumps(alert))
                print(f"Alert #{alert_id} stored — txn {alert['transaction_id']}", flush=True)
        except Exception as exc:
            print(f"Alert service error: {exc}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
