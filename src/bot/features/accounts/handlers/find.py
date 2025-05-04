from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, or_

from src.bot.features.accounts.keyboards import (
    accounts_keyboard,
    accounts_actions_keyboard,
)
from src.bot.triggers import Texts
from src.bot.features.accounts.states import AccountsStates
from src.core.clients.databases.postgres import pg
from src.core.models import Account

router = Router()


@router.message(F.text == Texts.Accounts.FIND)
async def ask_api_key(message: Message, state: FSMContext):
    await state.set_state(AccountsStates.waiting_api_key_or_name)
    await message.answer(
        "Пришлите публичный API-ключ аккаунта или его название:",
    )


@router.message(StateFilter(AccountsStates.waiting_api_key_or_name))
async def show_account_info(message: Message, state: FSMContext):
    key_or_name = message.text.strip()

    async with pg.session_maker() as session:
        stmt = select(Account).where(
            or_(Account.api_key == key_or_name, Account.name == key_or_name)
        )
        account = await session.scalar(stmt)

    if not account:
        await message.answer("Аккаунт не найден.", reply_markup=accounts_keyboard())
        return

    await state.update_data(account_id=account.id)
    await state.set_state(AccountsStates.account_selected)

    info = (
        f"🆔 ID: {account.id}\n"
        f"📛 Название: {account.name}\n"
        f"🔑 API Key: `{account.api_key}`\n"
        f"🏷 Биржа: {account.exchange}\n"
        f"⏱ Создан: {account.created_at:%Y-%m-%d %H:%M:%S}\n"
    )

    await message.answer(
        info, parse_mode="Markdown", reply_markup=accounts_actions_keyboard()
    )
