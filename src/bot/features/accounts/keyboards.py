from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from src.bot.callbacks import Callbacks


def accounts_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Найти аккаунт",
                    callback_data=Callbacks.Accounts.FIND,
                )
            ],
            [
                InlineKeyboardButton(
                    text="Добавить аккаунт",
                    callback_data=Callbacks.Accounts.ADD,
                )
            ],
            [
                InlineKeyboardButton(
                    text="Удалить аккаунт",
                    callback_data=Callbacks.Accounts.DELETE,
                )
            ],
        ]
    )


def accounts_actions_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Баланс",
                    callback_data=Callbacks.Accounts.BALANCE,
                )
            ],
            [
                InlineKeyboardButton(
                    text="Выполнить ордер",
                    callback_data=Callbacks.Accounts.EXECUTE_ORDER,
                )
            ],
        ]
    )


# from aiogram.utils.keyboard import InlineKeyboardBuilder
# from src.constants import Exchanges

# def accounts_keyboard() -> InlineKeyboardBuilder:
#     builder = InlineKeyboardBuilder()
#     for acc in [f"{i}" * 10 for i in range(10)]:
#         builder.button(text=acc, callback_data=f"account:{acc}")
#     builder.adjust(1)
#     return builder.as_markup()
