from __future__ import annotations

import random
from typing import Optional

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery
from faker import Faker
from loguru import logger
from sqlalchemy import select, update

from src.bot.triggers import Callbacks
from src.bot.keyboards.start.start import get_welcome_keyboard
from src.core.clients.databases.postgres import pg
from src.core.models import (
    User,
    Account,
    DepositAddress,
    UserAccountLink,
    Chain,
    Proxy,
    FakeHeader,
)

# -------------------------------------------------------------------- #
#                         helpers                                       #
# -------------------------------------------------------------------- #
_fake = Faker()


def _gen_headers() -> dict:
    """Фейковые headers для Backpack‐API."""
    return {
        "User-Agent": _fake.user_agent(),
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Referer": "https://backpack.exchange",
        "Connection": "keep-alive",
    }


def _gen_cookies() -> dict:
    names = random.sample(
        [
            "sessionid",
            "csrftoken",
            "auth_token",
            "userid",
            "tracking",
            "refresh_token",
            "guest_token",
            "cartid",
        ],
        k=random.randint(2, 5),
    )
    return {n: _fake.uuid4() for n in names}


# -------------------------------------------------------------------- #
#                         FSM‑states                                    #
# -------------------------------------------------------------------- #
class AddAccount(StatesGroup):
    waiting_api_key = State()
    waiting_api_secret = State()
    waiting_parent_pubkey = State()
    waiting_country = State()  # только для MAIN
    waiting_wallet_tag = State()
    waiting_deposit_sol = State()


add_account = Router()


# -------------------------------------------------------------------- #
#                         STEP‑1  – /add_account                        #
# -------------------------------------------------------------------- #
@add_account.callback_query(F.data == Callbacks.Accounts.ADD)
async def step_api_key(cb: CallbackQuery, state: FSMContext):
    await state.set_state(AddAccount.waiting_api_key)
    await cb.message.edit_text("🔑 Пришлите PUBLIC‑API‑KEY аккаунта")
    await cb.answer()


@add_account.message(AddAccount.waiting_api_key)
async def step_secret(msg: Message, state: FSMContext):
    await state.update_data(api_key=msg.text.strip())
    await state.set_state(AddAccount.waiting_api_secret)
    await msg.answer("🔐 Теперь API‑SECRET")


# -------------------------------------------------------------------- #
#                         STEP‑2  – parent‑key                          #
# -------------------------------------------------------------------- #
@add_account.message(AddAccount.waiting_api_secret)
async def step_parent(msg: Message, state: FSMContext):
    await state.update_data(api_secret=msg.text.strip())
    await state.set_state(AddAccount.waiting_parent_pubkey)
    await msg.answer(
        "Если это SUB‑аккаунт – пришлите PUBLIC‑key родителя.\n"
        "Если это главный – напишите 0."
    )


@add_account.message(AddAccount.waiting_parent_pubkey)
async def process_parent(msg: Message, state: FSMContext):
    parent_key = msg.text.strip()

    async with pg.session_maker() as s:
        parent_id: Optional[int] = None
        parent_country: Optional[str] = None

        if parent_key != "0":
            parent: Account | None = await s.scalar(
                select(Account).where(Account.api_key == parent_key)
            )
            if parent is None:
                await msg.answer(
                    "❌ Родитель с таким ключом не найден. Попробуйте ещё раз."
                )
                return
            parent_id = parent.id
            parent_country = parent.country

        await state.update_data(parent_id=parent_id, country=parent_country)

    # если страна уже известна (SUB), пропускаем вопрос
    if parent_country:
        await state.set_state(AddAccount.waiting_wallet_tag)
        await msg.answer("🏷 Название/метка кошелька")
    else:
        await state.set_state(AddAccount.waiting_country)
        await msg.answer("🌍 Страна (две буквы: DE, US, …)")


# -------------------------------------------------------------------- #
#                         STEP‑3  – country / wallet / deposit          #
# -------------------------------------------------------------------- #
@add_account.message(AddAccount.waiting_country)
async def step_wallet_after_country(msg: Message, state: FSMContext):
    await state.update_data(country=msg.text.strip().upper())
    await state.set_state(AddAccount.waiting_wallet_tag)
    await msg.answer("🏷 Название/метка кошелька")


@add_account.message(AddAccount.waiting_wallet_tag)
async def step_deposit(msg: Message, state: FSMContext):
    await state.update_data(wallet=msg.text.strip())
    await state.set_state(AddAccount.waiting_deposit_sol)
    await msg.answer("💳 SOL‑депозитный адрес")


@add_account.message(AddAccount.waiting_deposit_sol)
async def finish_save(msg: Message, state: FSMContext):
    await state.update_data(deposit_sol=msg.text.strip())

    data = await state.get_data()

    async with pg.session_maker() as session:
        # ─── USER ────────────────────────────────────────────────
        user = await session.scalar(
            select(User).where(User.telegram_id == str(msg.from_user.id))
        )
        if user is None:
            user = User(
                telegram_id=str(msg.from_user.id), username=msg.from_user.username
            )
            session.add(user)
            await session.flush()

        # ─── ACCOUNT OBJECT ──────────────────────────────────────
        account = Account(
            name=f"{data['wallet']} ({'sub' if data['parent_id'] else 'main'})",
            api_key=data["api_key"],
            api_secret=data["api_secret"],
            country=data["country"],
            wallet=data["wallet"],
            parent_id=data["parent_id"],
        )
        session.add(account)
        await session.flush()  # account.id

        # ─── PROXY pick & lock ───────────────────────────────────
        proxy = await session.scalar(
            select(Proxy)
            .where(
                Proxy.country == account.country,
                Proxy.in_use.is_(False),
                Proxy.account_id.is_(None),
            )
            .limit(1)
        )
        if proxy is None:
            await session.rollback()
            await state.clear()
            await msg.answer(
                "❌ Нет свободных прокси для страны.",
                reply_markup=get_welcome_keyboard(),
            )
            return

        await session.execute(
            update(Proxy)
            .where(Proxy.id == proxy.id)
            .values(account_id=account.id, in_use=True)
        )

        # ─── DEPOSIT address  ───────────────────────────────────
        session.add(
            DepositAddress(
                account_id=account.id,
                chain=Chain.SOLANA,
                address=data["deposit_sol"],
            )
        )

        # ─── Fake headers / cookies ─────────────────────────────
        session.add(
            FakeHeader(
                account_id=account.id, headers=_gen_headers(), cookies=_gen_cookies()
            )
        )

        # ─── ACL  ────────────────────────────────────────────────
        session.add(
            UserAccountLink(user_id=user.id, account_id=account.id, is_admin=True)
        )

        await session.commit()

    await state.clear()
    await msg.answer(
        "✅ Аккаунт, прокси и фейковые headers успешно сохранены!",
        reply_markup=get_welcome_keyboard(),
    )
