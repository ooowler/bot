from aiogram.utils.keyboard import InlineKeyboardBuilder


def exchange_keyboard(exchanges: list[str]):
    builder = InlineKeyboardBuilder()
    for name in exchanges:
        builder.button(text=name, callback_data=f"exchange:{name}")
    return builder.as_markup()
