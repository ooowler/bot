from aiogram import Dispatcher
from src.bot.handlers.start import start_router
from src.bot.handlers.add_account import add_account
from src.bot.handlers.account import account_router
from src.bot.handlers.delete_account import delete_router
from src.bot.handlers.add_proxy import add_proxy_router
from src.bot.handlers.show_proxy import show_proxy_router
from src.bot.handlers.view_account_handler import view_account
from src.bot.handlers.pools import pools_router
from src.bot.handlers.home import home_router


def register_all_handlers(dp: Dispatcher):
    dp.include_router(start_router)
    dp.include_router(add_account)
    dp.include_router(account_router)
    dp.include_router(view_account)
    dp.include_router(delete_router)
    dp.include_router(add_proxy_router)
    dp.include_router(show_proxy_router)
    dp.include_router(home_router)
    dp.include_router(pools_router)
