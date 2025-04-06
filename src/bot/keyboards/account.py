# src/bot/keyboards/account_kb.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from src.bot.callbacks import CallbackData


def get_welcome_keyboard():
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Добавить аккаунт", callback_data=CallbackData.ADD_ACCOUNT
                )
            ]
        ]
    )
    return kb


def get_exchanges_kb():
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Backpack", callback_data=CallbackData.EXCHANGE_BACKPACK
                )
            ]
        ]
    )
    return kb
