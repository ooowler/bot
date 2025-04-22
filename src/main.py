import os
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from loguru import logger
from dotenv import load_dotenv
from src.core.clients.databases.postgres import pg

from src.bot.handlers import register_all_handlers

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


async def tmp():
    from src.core.clients.exchanges.backpack.backpack import BackpackExchangeClient

    main = BackpackExchangeClient(
        base_url="https://api.backpack.exchange/",
        api_key=os.getenv("TEST_API_KEY"),
        api_secret=os.getenv("TEST_API_SECRET"),
    )

    sub = BackpackExchangeClient(
        base_url="https://api.backpack.exchange/",
        api_key=os.getenv("TEST_SUB_API_KEY"),
        api_secret=os.getenv("TEST_SUB_API_SECRET"),
    )
    await main.change_proxy()

    # sub_balance = await sub.get_balance()
    # print(f"sub_balance: {sub_balance}")

    # sub_borrow_lend_positions = await sub.get_borrow_lend_positions()
    # print(f"sub_borrow_lend_positions: {sub_borrow_lend_positions}")

    # get_order_book_depth = await sub.get_order_book_depth("AAVE_USDC")
    # print(f"get_order_book_depth: {get_order_book_depth}")

    # get_all_tickers = await sub.get_all_tickers()
    # print(f"get_all_tickers: {get_all_tickers}")

    # response = await main.request_withdrawal(
    #     address=os.getenv("TEST_SUB_DEP_SOL_ADDR"),
    #     blockchain="Solana",
    #     symbol="SOL",
    #     quantity="0.000001",
    #     auto_borrow=False,
    #     auto_lend_redeem=False,
    # )
    # print("Withdraw response:", response)

    # order_result = await main.create_order(
    #     symbol="JUP_USDC",
    #     side="Ask",  # Продаём
    #     quantity="0.15",
    #     order_type="Limit",
    #     price="0.45",  # Твоя целевая цена за монету
    # )
    # print("Лимитный ордер:", order_result)

    # order_result = await main.create_order(
    #     symbol="JUP_USDC",
    #     side="Ask",  # Продаём
    #     quantity="0.15",
    #     order_type="Market"
    # )
    # print("Маркет ордер:", order_result)

    # print(await main.get_open_orders())  # Все открытые ордера SPOT
    # или
    # print(await main.get_open_orders(symbol="SOL_USDC"))

    # convert_all_to_usdc = await main.convert_all_to_usdc(order_type="Limit")
    # print("✅ Массовая продажа лимитками:", convert_all_to_usdc)

    # print(await main.buy_token_with_stables("SOL_USDC", percent=100))

    # order_result = await main.create_order(
    #     symbol="ETH_USDC_PERP",
    #     side="Ask",  # Продаём
    #     quantity="0.002",
    #     order_type="Market"
    # )
    # print("Маркет ордер:", order_result)

    # orders = await main.get_open_orders(market_type="PERP")
    # print(orders)

    # open_positions = await main.get_open_positions()
    # print(open_positions)

    # print(f"close: {await main.close_all_perp_positions()}")

    # open_positions = await main.get_open_positions()
    # print(open_positions)

    # print(f"acc: {await main.get_account_info()}")
    # print(f"update: {await main.update_account_settings(leverage_limit=10)}")
    # print(f"acc2: {await main.get_account_info()}")


async def main():
    # await tmp()
    # return
    from prometheus_client import start_http_server

    start_http_server(8000)

    logger.info("Запускаем Telegram бота")
    bot = Bot(token=TELEGRAM_TOKEN)
    storage = RedisStorage.from_url(REDIS_URL)
    dp = Dispatcher(storage=storage)

    # from prometheus_client import start_http_server
    # start_http_server(8000)

    register_all_handlers(dp)

    logger.info("Начинаем polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
