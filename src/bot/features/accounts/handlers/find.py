from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import StateFilter, Command
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, or_

from src.bot.features.accounts.keyboards import (
    accounts_actions_keyboard,
    accounts_keyboard,
)
from src.bot.callbacks import Callbacks
from src.bot.features.accounts.states import AccountsStates
from src.core.clients.databases.postgres import pg
from src.core.models import Account

router = Router()


@router.callback_query(F.data == Callbacks.Accounts.FIND)
async def ask_api_key(cb: CallbackQuery, state: FSMContext):
    await state.set_state(AccountsStates.waiting_api_key_or_name)
    await cb.message.edit_text("Пришлите публичный апи ключ аккаунта или его название")
    await cb.answer()


@router.message(StateFilter(AccountsStates.waiting_api_key_or_name))
async def show_account_info(msg: Message, state: FSMContext):
    key_or_name = msg.text.strip()
    async with pg.session_maker() as session:
        stmt = select(Account).where(
            or_(Account.api_key == key_or_name, Account.name == key_or_name)
        )
        account = await session.scalar(stmt)

    if not account:
        await msg.answer("Аккаунт не найден.", reply_markup=accounts_keyboard())
        return

    info = (
        f"🆔 ID: {account.id}\n"
        f"📛 Название: {account.name}\n"
        f"🔑 API Key: `{account.api_key}`\n"
        f"🏷 Exchange: {account.exchange}\n"
        f"⏱ Создан: {account.created_at:%Y-%m-%d %H:%M:%S}\n"
    )

    await state.update_data(account_id=account.id)

    await msg.answer(
        info, parse_mode="Markdown", reply_markup=accounts_actions_keyboard()
    )
