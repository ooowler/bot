from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from loguru import logger
from sqlalchemy.exc import IntegrityError
from src.core.clients.databases.postgres import pg
from src.bot.callbacks import Callbacks
from src.bot.keyboards.exchanges.exchanges import (
    get_exchanges_keyboard,
    get_exchanges_actions_keyboard,
)
from src.bot.states.account import AddAccount, ExecuteAccount
from src.bot.keyboards.start.start import get_welcome_keyboard

account_router = Router()


@account_router.callback_query(F.data == Callbacks.Accounts.INFO)
async def on_add_account(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "Выберите биржу:", reply_markup=get_exchanges_keyboard()
    )


@account_router.callback_query(F.data == Callbacks.Exchanges.BACKPACK)
async def on_add_account(callback: CallbackQuery, state: FSMContext):
    await state.update_data(exchange="backpack")
    await callback.message.edit_text(
        "Выберите действие:", reply_markup=get_exchanges_actions_keyboard()
    )
