from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from loguru import logger
from sqlalchemy import select

from src.core.clients.databases.postgres import pg
from src.core.models.base import (
    User,
    Account,
    DepositAddress,
    UserAccountLink,
    Chain,
)
from src.bot.callbacks import Callbacks
from src.bot.states.add_account import AddAccount
from src.bot.keyboards.start.start import get_welcome_keyboard

add_account = Router()


@add_account.callback_query(F.data == Callbacks.Accounts.ADD)
async def add_account_start(cb: CallbackQuery, state: FSMContext):
    """Первый шаг – спрашиваем API‑KEY."""
    await state.set_state(AddAccount.waiting_api_key)
    await cb.message.edit_text("🔑 Пришли API‑KEY")
    await cb.answer()  # закрыть спиннер


@add_account.message(AddAccount.waiting_api_key)
async def add_account_api_key(msg: Message, state: FSMContext):
    await state.update_data(api_key=msg.text.strip())
    await state.set_state(AddAccount.waiting_api_secret)
    await msg.answer("🔐 Теперь API‑SECRET")


@add_account.message(AddAccount.waiting_api_secret)
async def add_account_api_secret(msg: Message, state: FSMContext):
    await state.update_data(api_secret=msg.text.strip())
    await state.set_state(AddAccount.waiting_country)
    await msg.answer("🌍 Страна (например, germany)")


@add_account.message(AddAccount.waiting_country)
async def add_account_country(msg: Message, state: FSMContext):
    await state.update_data(country=msg.text.strip().lower())
    await state.set_state(AddAccount.waiting_wallet_tag)
    await msg.answer("🏷 Название/метка кошелька")


@add_account.message(AddAccount.waiting_wallet_tag)
async def add_account_wallet(msg: Message, state: FSMContext):
    await state.update_data(wallet=msg.text.strip())
    await state.set_state(AddAccount.waiting_deposit_sol)
    await msg.answer("💳 SOL‑депозитный адрес")


@add_account.message(AddAccount.waiting_deposit_sol)
async def add_account_deposit(msg: Message, state: FSMContext):
    await state.update_data(deposit_sol=msg.text.strip())
    await state.set_state(AddAccount.waiting_parent_id)
    await msg.answer(
        "Если это SUB‑аккаунт – пришли ID главного аккаунта.\nЕсли главный – напиши 0."
    )


@add_account.message(AddAccount.waiting_parent_id)
async def add_account_save(msg: Message, state: FSMContext):
    try:
        parent_id_int = int(msg.text.strip())
    except ValueError:
        await msg.answer("Нужно число. Попробуй ещё раз.")
        return

    data = await state.get_data()

    async with pg.session_maker() as session:
        stmt = select(User).where(User.telegram_id == str(msg.from_user.id))
        user_obj: User | None = (await session.execute(stmt)).scalar_one_or_none()
        if user_obj is None:
            user_obj = User(
                telegram_id=str(msg.from_user.id), username=msg.from_user.username
            )
            session.add(user_obj)
            await session.flush()

        account = Account(
            name=f"{data['wallet']} ({'sub' if parent_id_int else 'main'})",
            api_key=data["api_key"],
            api_secret=data["api_secret"],
            country=data["country"],
            wallet=data["wallet"],
            parent_id=parent_id_int or None,
        )
        session.add(account)
        await session.flush()

        session.add(
            DepositAddress(
                account_id=account.id,
                chain=Chain.SOLANA,
                address=data["deposit_sol"],
            )
        )

        session.add(
            UserAccountLink(user_id=user_obj.id, account_id=account.id, is_admin=True)
        )

        await session.commit()

    await state.clear()
    await msg.answer("✅ Аккаунт сохранён!", reply_markup=get_welcome_keyboard())
