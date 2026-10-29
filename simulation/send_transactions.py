"""
Send 10,000 synthetic transactions to the platform for live demo.
Usage: python simulation/send_transactions.py [--count 10000] [--rate 50]
"""
import argparse
import asyncio
import random
import time
import uuid

import httpx

GATEWAY = "http://localhost:8000"
CATEGORIES = [
    "shopping_net", "shopping_pos", "gas_transport", "grocery_pos",
    "entertainment", "food_dining", "health_fitness", "travel",
    "kids_pets", "personal_care", "home", "misc_net", "misc_pos",
]
MERCHANTS = {
    "shopping_net": ["Amazon", "eBay", "Shopify Store", "Etsy"],
    "shopping_pos": ["Best Buy", "Target", "Walmart", "Macy's"],
    "gas_transport": ["Shell", "BP", "Chevron", "ExxonMobil"],
    "grocery_pos": ["Loblaws", "Sobeys", "Metro", "Whole Foods"],
    "entertainment": ["Netflix", "Spotify", "AMC Theatres", "Steam"],
    "food_dining": ["McDonald's", "Starbucks", "DoorDash", "Uber Eats"],
    "health_fitness": ["GoodLife Fitness", "Pharmacy Plus", "CVS"],
    "travel": ["Air Canada", "Marriott", "Expedia", "Airbnb"],
    "kids_pets": ["PetSmart", "Toys R Us", "Build-A-Bear"],
    "personal_care": ["Sephora", "The Body Shop", "Salon Noir"],
    "home": ["IKEA", "Home Depot", "Canadian Tire"],
    "misc_net": ["Unknown Online Store", "VPN Service", "Crypto Exchange"],
    "misc_pos": ["Corner Store", "Pawn Shop", "Unknown Merchant"],
}


def make_transaction(fraud_bias: float = 0.15) -> dict:
    is_fraud_scenario = random.random() < fraud_bias
    category = random.choice(CATEGORIES)

    if is_fraud_scenario:
        amount = round(random.uniform(800, 8000), 2)
        hour = random.choice([22, 23, 0, 1, 2, 3])
        category = random.choice(["misc_net", "shopping_net", "travel", "entertainment"])
        geo_dist = round(random.uniform(500, 2000), 1)
    else:
        amount = round(random.uniform(5, 250), 2)
        hour = random.randint(8, 21)
        geo_dist = round(random.uniform(0, 50), 1)

    merchant_list = MERCHANTS.get(category, ["Unknown"])
    return {
        "transaction_id": str(uuid.uuid4()),
        "amount": amount,
        "merchant_category": category,
        "merchant_name": random.choice(merchant_list),
        "cardholder_id": f"CH{random.randint(1000, 9999)}",
        "hour_of_day": hour,
        "day_of_week": random.randint(0, 6),
        "geo_dist": geo_dist,
    }


async def login(client: httpx.AsyncClient) -> str:
    res = await client.post(f"{GATEWAY}/auth/login", json={"username": "admin", "password": "admin123"})
    res.raise_for_status()
    return res.json()["access_token"]


async def send_batch(client: httpx.AsyncClient, token: str, txns: list, results: dict):
    headers = {"Authorization": f"Bearer {token}"}
    for txn in txns:
        try:
            res = await client.post(f"{GATEWAY}/transactions", json=txn, headers=headers, timeout=5.0)
            if res.status_code in (200, 202):
                results["ok"] += 1
            else:
                results["err"] += 1
        except Exception:
            results["err"] += 1


async def main(count: int, rate: int):
    print(f"Sending {count} transactions at ~{rate}/s to {GATEWAY}")
    async with httpx.AsyncClient() as client:
        try:
            token = await login(client)
            print("Authenticated successfully")
        except Exception as e:
            print(f"Login failed: {e}. Make sure `make up` is running.")
            return

        results = {"ok": 0, "err": 0}
        batch_size = max(1, rate // 10)
        delay = batch_size / rate

        start = time.monotonic()
        sent = 0

        while sent < count:
            this_batch = min(batch_size, count - sent)
            txns = [make_transaction(fraud_bias=0.18) for _ in range(this_batch)]
            await send_batch(client, token, txns, results)
            sent += this_batch

            elapsed = time.monotonic() - start
            actual_rate = sent / elapsed if elapsed > 0 else rate
            print(f"\r  {sent}/{count} sent | {results['ok']} ok | {results['err']} err | {actual_rate:.0f} txn/s", end="", flush=True)

            await asyncio.sleep(delay)

        elapsed = time.monotonic() - start
        print(f"\n\nDone in {elapsed:.1f}s — {results['ok']} succeeded, {results['err']} failed")
        print(f"Expect ~{int(count * 0.18)} flagged alerts in the dashboard")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulate transaction traffic")
    parser.add_argument("--count", type=int, default=10_000)
    parser.add_argument("--rate", type=int, default=50, help="transactions per second")
    args = parser.parse_args()
    asyncio.run(main(args.count, args.rate))
