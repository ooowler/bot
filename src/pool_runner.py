# src/bot/services/pool_runner.py
import asyncio
from loguru import logger
from dotenv import load_dotenv

from src.worker.pool_worker import run_pools_forever

load_dotenv()


async def main():
    logger.info("🚀 Запуск пул-демона…")
    await run_pools_forever()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Пул-демон остановлен вручную")
