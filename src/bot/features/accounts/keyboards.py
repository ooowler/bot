from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def accounts_keyboard(accounts: list[str]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    for acc in accounts:
        kb.add(InlineKeyboardButton(text=acc, callback_data=f"account:{acc}"))
    return kb
