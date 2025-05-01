from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="/select_exchange")],
            [KeyboardButton(text="/accounts"), KeyboardButton(text="/pools")],
            [KeyboardButton(text="/proxy")],
        ],
        resize_keyboard=True,
    )
