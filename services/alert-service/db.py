import os
import asyncpg

DSN = "postgresql://{user}:{password}@{host}:{port}/{db}".format(
    user=os.getenv("POSTGRES_USER", "monitor"),
    password=os.getenv("POSTGRES_PASSWORD", "monitor123"),
    host=os.getenv("POSTGRES_HOST", "postgres"),
    port=os.getenv("POSTGRES_PORT", "5432"),
    db=os.getenv("POSTGRES_DB", "monitoring"),
)

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(DSN, min_size=2, max_size=10)
    return _pool


async def insert_alert(alert: dict) -> int:
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        INSERT INTO alerts
            (transaction_id, amount, merchant_category, merchant_name,
             cardholder_id, hour_of_day, day_of_week, geo_dist,
             fraud_probability, rule_flags, risk_level)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
        ON CONFLICT (transaction_id) DO NOTHING
        RETURNING id
        """,
        alert["transaction_id"],
        alert.get("amount"),
        alert.get("merchant_category"),
        alert.get("merchant_name"),
        alert.get("cardholder_id"),
        alert.get("hour_of_day"),
        alert.get("day_of_week"),
        alert.get("geo_dist"),
        alert.get("fraud_probability"),
        alert.get("rule_flags", []),
        alert.get("risk_level", "HIGH"),
    )
    return row["id"] if row else -1
