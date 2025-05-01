import asyncio
from loguru import logger
from sqlalchemy import select

from src.core.clients.databases.postgres import pg
from src.core.models.pool import Pool
from src.bot.services.pools.subacc_trading_strategy import run_subacc_trading_strategy
from dotenv import load_dotenv

load_dotenv()


async def run_pools_forever():
    logger.info("🚀 Пул-демон запущен…")
    while True:
        try:
            async with pg.session_maker() as session:
                pools = (
                    await session.scalars(select(Pool).where(Pool.is_active.is_(True)))
                ).all()

            for pool in pools:
                # только для SUB_ACC_REQUIRED типа
                if pool.pool_type.lower() == "sub_required":
                    await run_subacc_trading_strategy(pool.id)
        except Exception as e:
            logger.error(f"POOL ERROR: {e}")

        await asyncio.sleep(60 * 45)


async def main():
    from prometheus_client import start_http_server

    start_http_server(8001)

    logger.info("🚀 Запуск пул-демона…")
    await run_pools_forever()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Пул-демон остановлен вручную")
