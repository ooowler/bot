from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from src.bot.triggers import Texts


def accounts_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=Texts.Accounts.FIND)],
            [KeyboardButton(text=Texts.Accounts.ADD)],
            [KeyboardButton(text=Texts.Accounts.ADD_CSV)],
            [KeyboardButton(text=Texts.Accounts.DELETE)],
            [KeyboardButton(text=Texts.Accounts.STATS)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def accounts_actions_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=Texts.Accounts.BALANCE)],
            [KeyboardButton(text=Texts.Accounts.ORDER)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
