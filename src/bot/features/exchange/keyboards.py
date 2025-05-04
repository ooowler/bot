from aiogram.utils.keyboard import InlineKeyboardBuilder
from src.constants import Exchanges


def exchange_keyboard():
    builder = InlineKeyboardBuilder()
    for exchange in Exchanges:
        name = exchange.value
        builder.button(text=name, callback_data=f"exchange={name}")
    return builder.as_markup()
