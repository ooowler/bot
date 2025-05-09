from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

from src.bot.triggers import Texts
from src.bot.features.pools.keyboards import get_main_keyboard
from src.bot.features.pools.states import PoolStates
from src.core.repositories.pools import (
    create_pool,
    add_account_to_pool,
    remove_account_from_pool,
    list_pools_for_user,
    list_pool_accounts,
)
from src.core.repositories.user import ensure_user

router = Router()


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Отмена")]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


# --- Handlers ---
@router.message(F.text == Texts.Pools.HOME)
async def pool_menu(message: Message, state: FSMContext):
    # ensure user in DB
    await ensure_user(message.from_user.id, message.from_user.username)
    await state.set_state(PoolStates.menu)
    await message.answer(
        "Выберите действие для управления пулами:", reply_markup=get_main_keyboard()
    )


@router.message(F.text == "Отмена")
async def cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Операция отменена.", reply_markup=get_main_keyboard())


@router.message(F.text == "Создать пул", StateFilter(PoolStates.menu))
# Создать пул
async def menu_create(message: Message, state: FSMContext):
    await state.set_state(PoolStates.create_label)
    await message.answer(
        "Введите название нового пула:", reply_markup=get_cancel_keyboard()
    )


@router.message(PoolStates.create_label)
async def process_create_label(message: Message, state: FSMContext):
    pool = await create_pool(
        label=message.text.strip(), owner_telegram_id=message.from_user.id
    )
    await message.answer(
        f"✅ Пул «{pool.label}» создан (ID={pool.id}).",
        reply_markup=get_main_keyboard(),
    )
    await state.clear()


# Add account
@router.message(F.text == "Добавить аккаунт", StateFilter(PoolStates.menu))
async def menu_add(message: Message, state: FSMContext):
    await state.set_state(PoolStates.add_pool_id)
    await message.answer(
        "Введите ID пула для добавления аккаунта:", reply_markup=get_cancel_keyboard()
    )


@router.message(PoolStates.add_pool_id)
async def process_add_pool_id(message: Message, state: FSMContext):
    await state.update_data(pool_id=int(message.text.strip()))
    await state.set_state(PoolStates.add_account_id)
    await message.answer("Введите ID аккаунта:", reply_markup=get_cancel_keyboard())


@router.message(PoolStates.add_account_id)
async def process_add_account_id(message: Message, state: FSMContext):
    data = await state.get_data()
    account_id = int(message.text.strip())
    await add_account_to_pool(pool_id=data["pool_id"], account_id=account_id)
    await message.answer(
        f"✅ Аккаунт {account_id} добавлен в пул {data['pool_id']}.",
        reply_markup=get_main_keyboard(),
    )
    await state.clear()


# Remove account
@router.message(F.text == "Удалить аккаунт", StateFilter(PoolStates.menu))
async def menu_remove(message: Message, state: FSMContext):
    await state.set_state(PoolStates.remove_pool_id)
    await message.answer(
        "Введите ID пула для удаления аккаунта:", reply_markup=get_cancel_keyboard()
    )


@router.message(PoolStates.remove_pool_id)
async def process_remove_pool_id(message: Message, state: FSMContext):
    await state.update_data(pool_id=int(message.text.strip()))
    await state.set_state(PoolStates.remove_account_id)
    await message.answer("Введите ID аккаунта:", reply_markup=get_cancel_keyboard())


@router.message(PoolStates.remove_account_id)
async def process_remove_account_id(message: Message, state: FSMContext):
    data = await state.get_data()
    account_id = int(message.text.strip())
    await remove_account_from_pool(pool_id=data["pool_id"], account_id=account_id)
    await message.answer(
        f"✅ Аккаунт {account_id} удалён из пула {data['pool_id']}.",
        reply_markup=get_main_keyboard(),
    )
    await state.clear()


# List pools
@router.message(F.text == "Список пулов", StateFilter(PoolStates.menu))
async def menu_list_pools(message: Message, state: FSMContext):
    pools = await list_pools_for_user(owner_id=message.from_user.id)
    if not pools:
        await message.answer("У вас пока нет пулов.")
    else:
        text = "\n".join(
            f"{p.id}: {p.label} (active={p.is_active}, status={p.status})"
            for p in pools
        )
        await message.answer("Ваши пулы:\n" + text, reply_markup=get_main_keyboard())
    await state.clear()


# List accounts in pool
@router.message(F.text == "Список аккаунтов", StateFilter(PoolStates.menu))
async def menu_list_accounts(message: Message, state: FSMContext):
    await state.set_state(PoolStates.list_accounts_pool_id)
    await message.answer(
        "Введите ID пула для показа аккаунтов:", reply_markup=get_cancel_keyboard()
    )


@router.message(PoolStates.list_accounts_pool_id)
async def process_list_accounts(message: Message, state: FSMContext):
    pool_id = int(message.text.strip())
    accounts = await list_pool_accounts(pool_id=pool_id)
    if not accounts:
        await message.answer("В этом пуле нет аккаунтов.")
    else:
        text = "\n".join(f"{acc.id}: {acc.name}" for acc in accounts)
        await message.answer(
            "Аккаунты в пуле:\n" + text, reply_markup=get_main_keyboard()
        )
    await state.clear()
