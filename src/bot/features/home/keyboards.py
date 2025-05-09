from src.bot.triggers import Texts

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=Texts.Accounts.HOME),
                KeyboardButton(text=Texts.Pools.HOME),
                KeyboardButton(text=Texts.Proxy.HOME),
                KeyboardButton(text=Texts.Friends.HOME),
            ],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )
