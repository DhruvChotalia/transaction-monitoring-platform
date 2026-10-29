import os
from datetime import UTC, datetime

from motor.motor_asyncio import AsyncIOMotorClient

MONGO_HOST = os.getenv("MONGO_HOST", "mongodb")
MONGO_PORT = int(os.getenv("MONGO_PORT", 27017))
MONGO_DB = os.getenv("MONGO_DB", "event_logs")

_client: AsyncIOMotorClient | None = None


def get_collection():
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(f"mongodb://{MONGO_HOST}:{MONGO_PORT}")
    return _client[MONGO_DB]["raw_events"]


async def log_event(txn: dict) -> None:
    col = get_collection()
    await col.insert_one({**txn, "_ingested_at": datetime.now(UTC).isoformat()})
