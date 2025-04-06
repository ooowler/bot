import os
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from loguru import logger
from dotenv import load_dotenv

from src.bot.handlers import register_all_handlers

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

async def tmp():
    from src.bot.clients.exchange.backpack import BackpackExchangeClient
    acc = BackpackExchangeClient(
        base_url="https://api.backpack.exchange/",
        api_key=os.getenv("TEST_API_KEY"),
        api_secret=os.getenv("TEST_API_SECRET"),
    )
    r = await acc.get_balance()
    print(f"r: {r}")

async def main():
    await tmp()
    return


    logger.info("Запускаем Telegram бота")
    bot = Bot(token=TELEGRAM_TOKEN)
    storage = RedisStorage.from_url(REDIS_URL)
    dp = Dispatcher(storage=storage)

    register_all_handlers(dp)

    logger.info("Начинаем polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
