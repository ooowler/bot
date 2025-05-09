from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


# --- Keyboards ---
def get_main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Создать пул")],
            [KeyboardButton(text="Добавить аккаунт")],
            [KeyboardButton(text="Удалить аккаунт")],
            [
                KeyboardButton(text="Список пулов"),
                KeyboardButton(text="Список аккаунтов"),
            ],
            [KeyboardButton(text="Отмена")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
