import asyncpg
import os
from datetime import date, timedelta

pool = None


async def get_pool():
    global pool
    if pool is None:
        pool = await asyncpg.create_pool(
            os.getenv("DATABASE_URL"),
            min_size=2,
            max_size=10
        )
    return pool


async def fetch(query, *args):
    p = await get_pool()
    rows = await p.fetch(query, *args)
    return [dict(r) for r in rows]


async def fetchrow(query, *args):
    p = await get_pool()
    row = await p.fetchrow(query, *args)
    return dict(row) if row else None


async def fetchval(query, *args):
    p = await get_pool()
    return await p.fetchval(query, *args)


async def execute(query, *args):
    p = await get_pool()
    return await p.execute(query, *args)
