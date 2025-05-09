from aiogram.fsm.context import FSMContext
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from src.bot.triggers import Callbacks, Texts

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from src.bot.triggers import Texts


def proxy_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=Texts.Proxy.ADD)],
            [KeyboardButton(text=Texts.Proxy.STATS)],
            [KeyboardButton(text=Texts.Proxy.DELETE)],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )


def confirmation_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да", callback_data=Callbacks.Proxy.CONFIRM)],
            [
                InlineKeyboardButton(
                    text="❌ Отмена", callback_data=Callbacks.Proxy.CANCEL
                )
            ],
        ]
    )
