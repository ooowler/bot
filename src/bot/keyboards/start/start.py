from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from src.bot.triggers import Callbacks


def get_welcome_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Аккаунты", callback_data=Callbacks.Accounts.INFO
                ),
                # InlineKeyboardButton(text="Пулы", callback_data=Callbacks.Pools.INFO),
            ],
            [
                # InlineKeyboardButton(
                #    text="Настройки", callback_data=Callbacks.User.SETTINGS
                # ),
                # InlineKeyboardButton(text="Прокси", callback_data=Callbacks.Proxy.INFO),
            ],
        ]
    )
