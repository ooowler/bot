from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from src.bot.triggers import Texts
from src.bot.features.accounts.keyboards import accounts_keyboard
from src.bot.features.accounts.states import AccountsStates
from src.core.clients.databases.postgres import pg
from src.core.models import Account

router = Router()


@router.message(F.text == Texts.Accounts.DELETE)
async def delete_account_start(message: Message, state: FSMContext):
    await state.set_state(AccountsStates.waiting_api_key_or_name_to_delete)
    await message.answer(
        "Введите API-ключ или название аккаунта для удаления:",
        reply_markup=accounts_keyboard(),
    )


@router.message(StateFilter(AccountsStates.waiting_api_key_or_name_to_delete))
async def delete_account_confirm(message: Message, state: FSMContext):
    ident = message.text.strip()
    async with pg.session_maker() as session:
        stmt = select(Account).where(
            (Account.api_key == ident) | (Account.name == ident)
        )
        account = await session.scalar(stmt)
        if not account:
            await message.answer(
                f"Аккаунт с идентификатором '{ident}' не найден.",
                reply_markup=accounts_keyboard(),
            )
            await state.clear()
            return
        await session.delete(account)
        await session.commit()
    await message.answer(
        f"Аккаунт '{account.name}' удалён.", reply_markup=accounts_keyboard()
    )
    await state.clear()
