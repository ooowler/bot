# src/bot/features/accounts/handlers/find.py
from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
)

from src.bot.features.accounts.keyboards import (
    accounts_keyboard,
    accounts_actions_keyboard,
)
from src.bot.features.accounts.states import AccountsStates
from src.bot.triggers import Texts
from src.core.repositories import accounts as accounts_repo

router = Router()


def _account_info(acc) -> str:
    return (
        f"🆔 ID: {acc.id}\n"
        f"📛 Название: {acc.name}\n"
        f"🔑 API Key: `{acc.api_key}`\n"
        f"🏷 Биржа: {acc.exchange}\n"
        f"⏱ Создан: {acc.created_at:%Y-%m-%d %H:%M:%S}\n"
    )


@router.message(F.text == Texts.Accounts.FIND)
async def find_choose_mode(message: Message, state: FSMContext) -> None:
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔍 Ввести ключ/имя")],
            [KeyboardButton(text="📄 Показать первые 20")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await state.set_state(AccountsStates.find_mode)
    await message.answer("Как хотите найти аккаунт?", reply_markup=kb)


@router.message(
    StateFilter(AccountsStates.find_mode),
    F.text == "🔍 Ввести ключ/имя",
)
async def find_mode_input(message: Message, state: FSMContext) -> None:
    await state.set_state(AccountsStates.waiting_api_key_or_name)
    await message.answer(
        "Введите публичный API-ключ или название аккаунта:",
        reply_markup=accounts_keyboard(),
    )


@router.message(
    StateFilter(AccountsStates.find_mode),
    F.text == "📄 Показать первые 20",
)
async def find_mode_list(message: Message, state: FSMContext) -> None:
    owner_tid = message.from_user.id
    accounts = await accounts_repo.fetch_accounts([owner_tid], with_friends=True)
    accounts = accounts[:20]

    if not accounts:
        await message.answer(
            "У вас ещё нет аккаунтов.", reply_markup=accounts_keyboard()
        )
        await state.clear()
        return

    buttons = [[KeyboardButton(text=acc.name or acc.api_key[:6])] for acc in accounts]
    kb = ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await state.set_state(AccountsStates.selecting_account)
    await message.answer("Выберите аккаунт:", reply_markup=kb)


@router.message(StateFilter(AccountsStates.waiting_api_key_or_name))
async def show_account_info(message: Message, state: FSMContext) -> None:
    key_or_name = message.text.strip()
    acc = await accounts_repo.get_by_api_or_name(key_or_name)
    if not acc:
        await message.answer("Аккаунт не найден.", reply_markup=accounts_keyboard())
        return

    await state.update_data(account_id=acc.id)
    await state.set_state(AccountsStates.account_selected)
    await message.answer(
        _account_info(acc),
        parse_mode="Markdown",
        reply_markup=accounts_actions_keyboard(),
    )


@router.message(StateFilter(AccountsStates.selecting_account))
async def find_select_from_list(message: Message, state: FSMContext) -> None:
    chosen = message.text.strip()
    acc = await accounts_repo.get_by_name(chosen)
    if not acc:
        await message.answer(
            "Аккаунт не найден. Пожалуйста, выберите из списка.",
            reply_markup=accounts_keyboard(),
        )
        return

    await state.update_data(account_id=acc.id)
    await state.set_state(AccountsStates.account_selected)
    await message.answer(
        _account_info(acc),
        parse_mode="Markdown",
        reply_markup=accounts_actions_keyboard(),
    )
