from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from src.constants import Exchanges


def exchange_keyboard() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=exchange.value)] for exchange in Exchanges],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    return kb
