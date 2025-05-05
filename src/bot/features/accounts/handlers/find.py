from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from src.bot.features.accounts.keyboards import (
    accounts_actions_keyboard,
    accounts_keyboard,
)
from src.bot.features.accounts.states import AccountsStates
from src.bot.triggers import Texts
from src.core.repositories import accounts as accounts_repo

router = Router()


@router.message(F.text == Texts.Accounts.FIND)
async def ask_api_key(message: Message, state: FSMContext) -> None:
    await state.set_state(AccountsStates.waiting_api_key_or_name)
    await message.answer("Пришлите публичный API‑ключ аккаунта или его название:")


@router.message(StateFilter(AccountsStates.waiting_api_key_or_name))
async def show_account_info(message: Message, state: FSMContext) -> None:
    key_or_name = message.text.strip()

    account = await accounts_repo.get_by_api_or_name(key_or_name)
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
