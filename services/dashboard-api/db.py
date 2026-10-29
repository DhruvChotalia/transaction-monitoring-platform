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


async def fetch_alerts(limit: int = 50, offset: int = 0) -> list:
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT * FROM alerts ORDER BY created_at DESC LIMIT $1 OFFSET $2",
        limit, offset,
    )
    return [dict(r) for r in rows]


async def fetch_stats() -> dict:
    pool = await get_pool()
    row = await pool.fetchrow("""
        SELECT
            COUNT(*)                                         AS total_alerts,
            COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '1 hour')  AS alerts_last_hour,
            ROUND(AVG(fraud_probability)::numeric, 4)        AS avg_fraud_prob,
            ROUND(SUM(amount)::numeric, 2)                   AS total_flagged_amount,
            COUNT(*) FILTER (WHERE risk_level = 'HIGH')      AS high_risk_count
        FROM alerts
    """)
    return dict(row)


async def fetch_hourly_distribution() -> list:
    pool = await get_pool()
    rows = await pool.fetch("""
        SELECT hour_of_day, COUNT(*) AS alert_count, ROUND(AVG(fraud_probability)::numeric, 4) AS avg_prob
        FROM alerts
        GROUP BY hour_of_day
        ORDER BY hour_of_day
    """)
    return [dict(r) for r in rows]


async def fetch_category_breakdown() -> list:
    pool = await get_pool()
    rows = await pool.fetch("""
        SELECT merchant_category, COUNT(*) AS alert_count, ROUND(SUM(amount)::numeric, 2) AS total_amount
        FROM alerts
        GROUP BY merchant_category
        ORDER BY alert_count DESC
        LIMIT 10
    """)
    return [dict(r) for r in rows]


async def fetch_rules() -> list:
    pool = await get_pool()
    rows = await pool.fetch("SELECT * FROM rules ORDER BY severity DESC, name")
    return [dict(r) for r in rows]
