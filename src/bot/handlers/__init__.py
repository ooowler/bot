from aiogram import Dispatcher
from src.bot.handlers.start import start_router
from src.bot.handlers.account import account_router


def register_all_handlers(dp: Dispatcher):
    dp.include_router(start_router)
    dp.include_router(account_router)
