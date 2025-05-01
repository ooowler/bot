from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def pools_keyboard(pools: list[str]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    for p in pools:
        kb.add(InlineKeyboardButton(text=p, callback_data=f"pool:{p}"))
    return kb
