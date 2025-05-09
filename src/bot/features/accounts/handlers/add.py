# src/bot/features/accounts/handlers/add.py
from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
import random
from faker import Faker

from src.bot.features.accounts.keyboards import accounts_keyboard
from src.bot.features.accounts.states import AccountsStates
from src.bot.triggers import Texts
from src.core.models import Account, FakeHeader, DepositAddress, Chain
from src.core.repositories import accounts as accounts_repo
from src.exceptions import NoFreeProxy

router = Router()
_fake = Faker()


# ───────── helpers ─────────
def _gen_headers() -> dict[str, str]:
    return {
        "User-Agent": _fake.user_agent(),
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
    }


def _gen_cookies() -> dict[str, str]:
    names = random.sample(
        ["sessionid", "csrftoken", "auth_token", "userid", "tracking", "cartid"],
        k=random.randint(2, 5),
    )
    return {n: _fake.uuid4() for n in names}


# ───────── FSM: шаги ввода данных ─────────
@router.message(F.text == Texts.Accounts.ADD)
async def add_account_start(message: Message, state: FSMContext) -> None:
    await state.set_state(AccountsStates.adding_name)
    await message.answer("Введите название аккаунта:", reply_markup=accounts_keyboard())


@router.message(StateFilter(AccountsStates.adding_name))
async def add_account_name(message: Message, state: FSMContext) -> None:
    await state.update_data(name=message.text.strip())
    await state.set_state(AccountsStates.adding_api_key)
    await message.answer(
        "Введите публичный API‑ключ:", reply_markup=accounts_keyboard()
    )


@router.message(StateFilter(AccountsStates.adding_api_key))
async def add_account_api_key(message: Message, state: FSMContext) -> None:
    await state.update_data(api_key=message.text.strip())
    await state.set_state(AccountsStates.adding_api_secret)
    await message.answer(
        "Введите приватный API‑секрет:", reply_markup=accounts_keyboard()
    )


@router.message(StateFilter(AccountsStates.adding_api_secret))
async def add_account_api_secret(message: Message, state: FSMContext) -> None:
    await state.update_data(api_secret=message.text.strip())
    await state.set_state(AccountsStates.adding_country)
    await message.answer("Введите страну:", reply_markup=accounts_keyboard())


@router.message(StateFilter(AccountsStates.adding_country))
async def add_account_country(message: Message, state: FSMContext) -> None:
    await state.update_data(country=message.text.strip().upper())
    await state.set_state(AccountsStates.adding_deposit)
    await message.answer(
        "Введите Solana‑адрес для депозита:", reply_markup=accounts_keyboard()
    )


# ───────── финальный шаг ─────────
@router.message(StateFilter(AccountsStates.adding_deposit))
async def add_account_deposit(message: Message, state: FSMContext) -> None:
    await state.update_data(deposit_address=message.text.strip())
    data = await state.get_data()

    # формируем готовые объекты
    account = Account(
        name=data["name"],
        api_key=data["api_key"],
        api_secret=data["api_secret"],
        exchange=data["exchange"],
        country=data["country"],
    )

    fake_header = FakeHeader(headers=_gen_headers(), cookies=_gen_cookies())

    deposit = DepositAddress(
        chain=Chain.SOLANA,
        address=data["deposit_address"],
    )

    # сохраняем через репозиторий
    try:
        proxy = await accounts_repo.add_account_full(
            account=account,
            fake_header=fake_header,
            deposit=deposit,
        )
    except NoFreeProxy as e:
        await message.answer(
            f"❌ Нет свободных прокси для страны {e}", reply_markup=accounts_keyboard()
        )
        await state.clear()
        return

    await message.answer(
        f"Аккаунт <b>{account.name}</b> добавлен.\n"
        f"Прокси: {proxy.ip}\n"
        f"Headers: {fake_header.headers}\n"
        f"Cookies: {fake_header.cookies}\n"
        f"Deposit: {deposit.address}",
        parse_mode="HTML",
        reply_markup=accounts_keyboard(),
    )
    await state.clear()
