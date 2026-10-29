import os

import httpx
from auth import DEMO_USERS, create_token, verify_password, verify_token
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

app = FastAPI(title="Transaction Monitoring — API Gateway", version="1.0.0")

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(app)

INGESTION_URL = os.getenv("INGESTION_URL", "http://ingestion:8001")
DASHBOARD_API_URL = os.getenv("DASHBOARD_API_URL", "http://dashboard-api:8006")
AI_EXPLAINER_URL = os.getenv("AI_EXPLAINER_URL", "http://ai-explainer:8005")


class LoginRequest(BaseModel):
    username: str
    password: str


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
    return {"status": "ok", "service": "api-gateway"}


@app.post("/auth/login")
@limiter.limit("10/minute")
async def login(request: Request, body: LoginRequest):
    hashed = DEMO_USERS.get(body.username)
    if not hashed or not verify_password(body.password, hashed):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"access_token": create_token(body.username), "token_type": "bearer"}


@app.post("/transactions", status_code=202)
@limiter.limit("1000/minute")
async def submit_transaction(
    request: Request,
    txn: Transaction,
    _user: str = Depends(verify_token),
):
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{INGESTION_URL}/ingest", json=txn.model_dump(), timeout=5)
        resp.raise_for_status()
    return {"status": "accepted", "transaction_id": txn.transaction_id}


@app.get("/alerts")
async def get_alerts(
    limit: int = 50,
    offset: int = 0,
    _user: str = Depends(verify_token),
):
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{DASHBOARD_API_URL}/alerts",
            params={"limit": limit, "offset": offset},
            timeout=5,
        )
        resp.raise_for_status()
    return resp.json()


@app.get("/alerts/{alert_id}/explanation")
async def get_explanation(alert_id: int, _user: str = Depends(verify_token)):
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{AI_EXPLAINER_URL}/explanation/{alert_id}", timeout=10)
        resp.raise_for_status()
    return resp.json()


@app.get("/stats")
async def get_stats(_user: str = Depends(verify_token)):
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{DASHBOARD_API_URL}/stats", timeout=5)
        resp.raise_for_status()
    return resp.json()


@app.get("/rules")
async def get_rules(_user: str = Depends(verify_token)):
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{DASHBOARD_API_URL}/rules", timeout=5)
        resp.raise_for_status()
    return resp.json()
