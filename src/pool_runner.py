# src/bot/services/pool_runner.py
import asyncio
from loguru import logger
from dotenv import load_dotenv

from src.worker.pool_worker import run_pools_forever

load_dotenv()


async def main():
    from prometheus_client import start_http_server

    start_http_server(8000)
    from prometheus_client import Counter

    TEST_COUNTER = Counter("telegram_test_requests_total", "Счётчик тестовых вызовов")
    TEST_COUNTER.inc()
    logger.info("🚀 Запуск пул-демона…")
    await run_pools_forever()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Пул-демон остановлен вручную")
