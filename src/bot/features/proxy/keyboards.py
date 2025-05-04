from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from src.bot.triggers import Texts


def proxy_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Добавить прокси")],
            [KeyboardButton(text=Texts.Proxy.STATS)],
            [KeyboardButton(text=Texts.Proxy.DELETE)],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )
