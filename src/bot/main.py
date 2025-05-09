# src/bot/main.py
import asyncio
from dotenv import load_dotenv
from loguru import logger
from prometheus_client import start_http_server
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage

import src.settings as settings
from src.dev import dev
from src.bot.common.middlewares import AccessMiddleware, MetricsMiddleware
from src.bot.features.home import router as home_router
from src.bot.features.exchange import router as exchange_router
from src.bot.features.accounts.handlers import (
    accounts_home_router,
    accounts_find_router,
    accounts_balance_router,
    accounts_stats_router,
    accounts_add_router,
    accounts_add_csv_router,
    accounts_delete_router,
    accounts_order_market_router,
    accounts_transfer_router,
    accounts_proxy_router,
)
from src.bot.features.pools import router as pools_router
from src.bot.features.friends import router as friends_router
from src.bot.features.proxy.handlers import (
    proxy_add_router,
    proxy_stats_router,
    proxy_delete_router,
)

load_dotenv()


async def main():
    if settings.DEV_MODE:
        await dev()
        return

    logger.info("Starting Prometheus on :8000")
    start_http_server(8000)

    logger.info("Starting Telegram bot")
    bot = Bot(token=settings.TELEGRAM_TOKEN)
    dp = Dispatcher(storage=RedisStorage.from_url(settings.REDIS_FSM_URL))

    dp.update.middleware.register(AccessMiddleware(settings.ALLOW))
    dp.message.middleware(MetricsMiddleware())
    dp.callback_query.middleware(MetricsMiddleware())

    dp.include_router(home_router)
    dp.include_router(exchange_router)
    dp.include_router(accounts_home_router)
    dp.include_router(accounts_find_router)
    dp.include_router(accounts_balance_router)
    dp.include_router(accounts_stats_router)
    dp.include_router(accounts_add_router)
    dp.include_router(accounts_add_csv_router)
    dp.include_router(accounts_delete_router)
    dp.include_router(accounts_order_market_router)
    dp.include_router(accounts_transfer_router)
    dp.include_router(accounts_proxy_router)
    dp.include_router(pools_router)
    dp.include_router(proxy_add_router)
    dp.include_router(proxy_stats_router)
    dp.include_router(proxy_delete_router)
    dp.include_router(friends_router)

    logger.info("Beginning polling")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
