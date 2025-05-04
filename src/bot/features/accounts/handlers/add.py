from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
import random
from faker import Faker
from sqlalchemy import select

from src.bot.triggers import Texts
from src.bot.features.accounts.keyboards import accounts_keyboard
from src.bot.features.accounts.states import AccountsStates
from src.core.clients.databases.postgres import pg
from src.core.models import Account, FakeHeader, Proxy, DepositAddress, Chain

router = Router()
_fake = Faker()


def _gen_headers() -> dict:
    return {
        "User-Agent": _fake.user_agent(),
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
    }


def _gen_cookies() -> dict:
    names = random.sample(
        ["sessionid", "csrftoken", "auth_token", "userid", "tracking", "cartid"],
        k=random.randint(2, 5),
    )
    return {n: _fake.uuid4() for n in names}


@router.message(F.text == Texts.Accounts.ADD)
async def add_account_start(message: Message, state: FSMContext):
    await state.set_state(AccountsStates.adding_name)
    await message.answer("Введите название аккаунта:", reply_markup=accounts_keyboard())


@router.message(StateFilter(AccountsStates.adding_name))
async def add_account_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(AccountsStates.adding_api_key)
    await message.answer(
        "Введите публичный API-ключ:", reply_markup=accounts_keyboard()
    )


@router.message(StateFilter(AccountsStates.adding_api_key))
async def add_account_api_key(message: Message, state: FSMContext):
    await state.update_data(api_key=message.text.strip())
    await state.set_state(AccountsStates.adding_api_secret)
    await message.answer(
        "Введите приватный API-секрет:", reply_markup=accounts_keyboard()
    )


@router.message(StateFilter(AccountsStates.adding_api_secret))
async def add_account_api_secret(message: Message, state: FSMContext):
    await state.update_data(api_secret=message.text.strip())
    await state.set_state(AccountsStates.adding_country)
    await message.answer("Введите страну:", reply_markup=accounts_keyboard())


@router.message(StateFilter(AccountsStates.adding_country))
async def add_account_country(message: Message, state: FSMContext):
    await state.update_data(country=message.text.strip())
    await state.set_state(AccountsStates.adding_deposit)
    await message.answer(
        "Введите solana адрес для депозита", reply_markup=accounts_keyboard()
    )


@router.message(StateFilter(AccountsStates.adding_deposit))
async def add_account_deposit(message: Message, state: FSMContext):
    await state.update_data(deposit_address=message.text.strip())
    data = await state.get_data()
    headers = _gen_headers()
    cookies = _gen_cookies()

    async with pg.session_maker() as session:
        account = Account(
            name=data["name"],
            api_key=data["api_key"],
            api_secret=data["api_secret"],
            exchange=data["exchange"],
            country=data["country"],
        )
        session.add(account)
        await session.flush()

        session.add(FakeHeader(account_id=account.id, headers=headers, cookies=cookies))

        proxy = await session.scalar(
            select(Proxy)
            .where(Proxy.country == data["country"], Proxy.in_use.is_(False))
            .limit(1)
        )
        if not proxy:
            await session.rollback()
            await message.answer(
                f"❌ Нет свободных прокси для страны {data['country']}",
                reply_markup=accounts_keyboard(),
            )
            await state.clear()
            return

        proxy.account_id = account.id
        proxy.in_use = True

        session.add(
            DepositAddress(
                account_id=account.id,
                chain=Chain.SOLANA,
                address=data["deposit_address"],
            )
        )

        await session.commit()

    await message.answer(
        f"Аккаунт {account.name} добавлен.\n"
        f"Прокси: {proxy.ip}\n"
        f"Headers: {headers}\n"
        f"Cookies: {cookies}\n"
        f"Deposit: {data['deposit_address']}",
        reply_markup=accounts_keyboard(),
    )
    await state.clear()
