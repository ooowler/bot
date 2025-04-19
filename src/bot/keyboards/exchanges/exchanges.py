from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from src.bot.callbacks import Callbacks


def get_exchanges_keyboard():
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Backpack", callback_data=Callbacks.Exchanges.BACKPACK
                )
            ]
        ]
    )
    return kb


def get_exchanges_actions_keyboard():
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Добавить аккаунт", callback_data=Callbacks.Accounts.ADD
                ),
                InlineKeyboardButton(
                    text="Посмотреть аккаунт", callback_data=Callbacks.Accounts.SHOW_ONE
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Выполнить ордер",
                    callback_data=Callbacks.Accounts.EXECUTE_ORDER,
                ),
            ],
        ]
    )
    return kb
