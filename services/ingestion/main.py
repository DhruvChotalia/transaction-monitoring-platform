from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel
from producer import publish_transaction
from mongo import log_event

app = FastAPI(title="Ingestion Service", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
Instrumentator().instrument(app).expose(app)


class Transaction(BaseModel):
    transaction_id: str
    amount: float
    merchant_category: str
    merchant_name: str
    cardholder_id: str
    hour_of_day: int
    day_of_week: int
    geo_dist: float


@app.get("/health")
def health():
    return {"status": "ok", "service": "ingestion"}


@app.post("/ingest", status_code=202)
async def ingest(txn: Transaction):
    payload = txn.model_dump()
    await log_event(payload)
    await publish_transaction(payload)
    return {"status": "queued", "transaction_id": txn.transaction_id}
