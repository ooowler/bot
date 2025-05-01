import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from loguru import logger
from dotenv import load_dotenv
from src.settings import DEV_MODE, TELEGRAM_TOKEN, REDIS_FSM_URL
from src.core.models import User
from src.core.clients.databases.postgres import pg
from prometheus_client import start_http_server
from src.bot.handlers import register_all_handlers

load_dotenv()


async def main():
    if DEV_MODE:
        from src.dev import dev

        await dev()
        return

    logger.info("Запускаем Prometheus клиента)")
    start_http_server(8000)

    logger.info("Запускаем Telegram бота")
    bot = Bot(token=TELEGRAM_TOKEN)
    dp = Dispatcher(storage=RedisStorage.from_url(REDIS_FSM_URL))

    register_all_handlers(dp)

    logger.info("Начинаем polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
