"""
End-to-end pipeline test.
Requires all services running: make up && make train-model
"""
import asyncio
import uuid
import pytest
import httpx

GATEWAY = "http://localhost:8000"
DASHBOARD = "http://localhost:8006"


async def get_token() -> str:
    async with httpx.AsyncClient() as client:
        res = await client.post(f"{GATEWAY}/auth/login", json={"username": "admin", "password": "admin123"})
        return res.json()["access_token"]


@pytest.mark.asyncio
async def test_health_endpoints():
    async with httpx.AsyncClient() as client:
        for port in [8000, 8001, 8002, 8003, 8004, 8005, 8006]:
            try:
                res = await client.get(f"http://localhost:{port}/health", timeout=3.0)
                assert res.status_code == 200, f"Service on port {port} unhealthy"
            except httpx.ConnectError:
                pytest.skip(f"Service on port {port} not reachable — run `make up`")


@pytest.mark.asyncio
async def test_login_returns_token():
    try:
        token = await get_token()
        assert token and len(token) > 20
    except httpx.ConnectError:
        pytest.skip("Gateway not running")


@pytest.mark.asyncio
async def test_high_risk_transaction_creates_alert():
    try:
        token = await get_token()
    except httpx.ConnectError:
        pytest.skip("Gateway not running")

    txn_id = str(uuid.uuid4())
    payload = {
        "transaction_id": txn_id,
        "amount": 9999.99,
        "merchant_category": "misc_net",
        "merchant_name": "Unknown Crypto Exchange",
        "cardholder_id": "CH9999",
        "hour_of_day": 3,
        "latitude": 51.5,
        "longitude": -0.1,
        "home_latitude": 43.6,
        "home_longitude": -79.4,
    }

    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {token}"}
        res = await client.post(f"{GATEWAY}/transactions", json=payload, headers=headers, timeout=5.0)
        assert res.status_code == 200

        await asyncio.sleep(3)

        alerts_res = await client.get(f"{GATEWAY}/alerts?limit=50", headers=headers, timeout=5.0)
        assert alerts_res.status_code == 200
        alerts = alerts_res.json()
        ids = [a.get("transaction_id") for a in alerts]
        assert txn_id in ids, f"Alert for {txn_id} not found in DB after 3s"


@pytest.mark.asyncio
async def test_stats_endpoint():
    try:
        token = await get_token()
    except httpx.ConnectError:
        pytest.skip("Gateway not running")

    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {token}"}
        res = await client.get(f"{GATEWAY}/stats", headers=headers, timeout=5.0)
        assert res.status_code == 200
        data = res.json()
        for field in ["total_alerts", "alerts_last_hour", "avg_fraud_prob"]:
            assert field in data


@pytest.mark.asyncio
async def test_analytics_endpoints():
    async with httpx.AsyncClient() as client:
        try:
            hourly = await client.get(f"{DASHBOARD}/analytics/hourly", timeout=3.0)
            cats = await client.get(f"{DASHBOARD}/analytics/categories", timeout=3.0)
            assert hourly.status_code == 200
            assert cats.status_code == 200
        except httpx.ConnectError:
            pytest.skip("Dashboard API not running")
