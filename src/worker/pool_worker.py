# src/worker/pool_worker.py
import asyncio
from loguru import logger
from sqlalchemy import select

from src.core.clients.databases.postgres import pg
from src.core.models.pool import Pool
from src.bot.services.pools.subacc_trading_strategy import run_subacc_trading_strategy


async def run_pools_forever():
    logger.info("🚀 Пул-демон запущен…")
    while True:
        async with pg.session_maker() as session:
            pools = (
                await session.scalars(select(Pool).where(Pool.is_active.is_(True)))
            ).all()

        for pool in pools:
            # только для SUB_ACC_REQUIRED типа
            if pool.pool_type.lower() == "sub_required":
                await run_subacc_trading_strategy(pool.id)

        await asyncio.sleep(60)
