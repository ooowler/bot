from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from src.bot.callbacks import Callbacks


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Выбрать биржу",
                    callback_data=Callbacks.Exchanges.SELECT,
                )
            ],
            [
                InlineKeyboardButton(
                    text="Аккаунты",
                    callback_data=Callbacks.Accounts.HOME,
                )
            ],
            [
                InlineKeyboardButton(
                    text="Пулы",
                    callback_data=Callbacks.Pools.HOME,
                )
            ],
            [
                InlineKeyboardButton(
                    text="Прокси",
                    callback_data=Callbacks.Proxy.HOME,
                )
            ],
        ]
    )
