from aiogram import Router, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from src.core.clients.databases.postgres import pg
from src.bot.callbacks import Callbacks
from src.bot.keyboards.start.start import get_welcome_keyboard

info_router = Router()

# ───────────────────────────── KEYBOARDS ──────────────────────────────


def get_account_actions_kb(acc_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📊 Баланс",
                    callback_data=f"{Callbacks.Accounts.GET_BALANCE}:{acc_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🛒 Выполнить ордер",
                    callback_data=f"{Callbacks.Accounts.EXECUTE_ORDER}:{acc_id}",
                )
            ],
        ]
    )
