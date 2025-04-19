from aiogram import Dispatcher
from src.bot.handlers.start import start_router
from src.bot.handlers.add_account import add_account
from src.bot.handlers.account import account_router
from src.bot.handlers.view_account_handler import view_account


def register_all_handlers(dp: Dispatcher):
    dp.include_router(start_router)
    dp.include_router(add_account)
    dp.include_router(account_router)
    dp.include_router(view_account)
