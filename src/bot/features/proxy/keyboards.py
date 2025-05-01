from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def proxy_keyboard(proxies: list[str]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    for p in proxies:
        kb.add(InlineKeyboardButton(text=p, callback_data=f"proxy:{p}"))
    return kb
