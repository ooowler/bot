from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from src.bot.features.accounts.keyboards import accounts_keyboard
from src.bot.features.accounts.states import AccountsStates
from src.bot.triggers import Texts
from src.core.repositories import accounts as accounts_repo

router = Router()


@router.message(F.text == Texts.Accounts.DELETE)
async def delete_account_start(message: Message, state: FSMContext) -> None:
    await state.set_state(AccountsStates.waiting_api_key_or_name_to_delete)
    await message.answer(
        "Введите API‑ключ или название аккаунта для удаления:",
        reply_markup=accounts_keyboard(),
    )


@router.message(StateFilter(AccountsStates.waiting_api_key_or_name_to_delete))
async def delete_account_confirm(message: Message, state: FSMContext) -> None:
    ident = message.text.strip()

    account = await accounts_repo.delete_by_api_or_name(ident)
    if not account:
        await message.answer(
            f"Аккаунт с идентификатором «{ident}» не найден.",
            reply_markup=accounts_keyboard(),
        )
        await state.clear()
        return

    await message.answer(
        f"Аккаунт «{account.name}» удалён.", reply_markup=accounts_keyboard()
    )
    await state.clear()
