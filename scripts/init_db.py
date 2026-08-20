"""Initialize Postgres schema and seed sample analytics data."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import asyncpg

from app.config import settings

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS energy_usage (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    unit VARCHAR(16) NOT NULL DEFAULT 'kWh',
    site_id VARCHAR(64) NOT NULL
);

CREATE TABLE IF NOT EXISTS revenue (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    amount DOUBLE PRECISION NOT NULL,
    region VARCHAR(64) NOT NULL,
    product VARCHAR(64) NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL,
    churned BOOLEAN NOT NULL DEFAULT FALSE,
    plan VARCHAR(32) NOT NULL
);
"""

async def init_db() -> None:
    conn = await asyncpg.connect(settings.database_url)
    try:
        await conn.execute(SCHEMA_SQL)

        energy_count = await conn.fetchval("SELECT COUNT(*) FROM energy_usage")
        if energy_count == 0:
            await conn.execute(
                """
                INSERT INTO energy_usage (timestamp, value, unit, site_id)
                SELECT
                    NOW() - (n || ' days')::interval,
                    80 + (random() * 40) + CASE WHEN n = 3 THEN 120 ELSE 0 END,
                    'kWh',
                    'site-a'
                FROM generate_series(1, 30) AS n
                """
            )

        revenue_count = await conn.fetchval("SELECT COUNT(*) FROM revenue")
        if revenue_count == 0:
            await conn.execute(
                """
                INSERT INTO revenue (date, amount, region, product)
                SELECT
                    CURRENT_DATE - n,
                    1000 + (random() * 500),
                    CASE WHEN n % 2 = 0 THEN 'EMEA' ELSE 'AMER' END,
                    CASE WHEN n % 3 = 0 THEN 'enterprise' ELSE 'starter' END
                FROM generate_series(1, 90) AS n
                """
            )

        users_count = await conn.fetchval("SELECT COUNT(*) FROM users")
        if users_count == 0:
            await conn.execute(
                """
                INSERT INTO users (created_at, churned, plan)
                SELECT
                    NOW() - (n || ' days')::interval,
                    n % 7 = 0,
                    CASE WHEN n % 2 = 0 THEN 'pro' ELSE 'free' END
                FROM generate_series(1, 200) AS n
                """
            )

        print("Database initialized successfully.")
    finally:
        await conn.close()


def main() -> None:
    asyncio.run(init_db())


if __name__ == "__main__":
    main()
