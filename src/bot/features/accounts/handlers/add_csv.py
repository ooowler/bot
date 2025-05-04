import csv
import os
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
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
    names = ["sessionid", "csrftoken", "auth_token", "userid", "tracking", "cartid"]
    return {
        n: _fake.uuid4()
        for n in _fake.random.sample(names, k=_fake.random.randint(2, 5))
    }


@router.message(F.text == Texts.Accounts.ADD_CSV)
async def import_start(message: Message, state: FSMContext):
    await state.set_state(AccountsStates.import_csv)
    await message.answer(
        "Пришлите CSV-файл с аккаунтами (столбцы NAME,API_KEY,API_SECRET,COUNTRY,SOL_DEPOSIT_ADDRESS,PARENT):",
        reply_markup=accounts_keyboard(),
    )


@router.message(StateFilter(AccountsStates.import_csv), F.document)
async def import_csv(message: Message, state: FSMContext):
    file = message.document
    if not file.file_name.lower().endswith(".csv"):
        await message.answer(
            "Неверный формат файла, прикрепите CSV.", reply_markup=accounts_keyboard()
        )
        return

    user_id = message.from_user.id
    data = await state.get_data()
    exchange = data["exchange"]
    path = f"/tmp/{file.file_unique_id}.csv"
    await message.bot.download(file, destination=path)
    successes, failures = [], []
    try:
        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            reader.fieldnames = [h.strip().upper() for h in reader.fieldnames]
            for idx, row in enumerate(reader, start=1):
                try:
                    data = {k.strip().upper(): v.strip() for k, v in row.items()}
                    name = data["NAME"]
                    api_key = data["API_KEY"]
                    api_secret = data["API_SECRET"]
                    country = data["COUNTRY"]
                    deposit_address = data["SOL_DEPOSIT_ADDRESS"]
                    parent_ident = data.get("PARENT") or None
                    headers = _gen_headers()
                    cookies = _gen_cookies()
                    async with pg.session_maker() as session:
                        parent_id = None
                        if parent_ident:
                            stmt = select(Account).where(
                                (Account.api_key == parent_ident)
                                | (Account.name == parent_ident)
                            )
                            parent = await session.scalar(stmt)
                            if not parent:
                                raise ValueError(f"Parent '{parent_ident}' not found")
                            parent_id = parent.id
                        account = Account(
                            name=name,
                            api_key=api_key,
                            api_secret=api_secret,
                            exchange=exchange,
                            country=country,
                            parent_id=parent_id,
                            owner_tid=int(user_id),
                        )
                        session.add(account)
                        await session.flush()
                        session.add(
                            FakeHeader(
                                account_id=account.id, headers=headers, cookies=cookies
                            )
                        )
                        proxy = await session.scalar(
                            select(Proxy)
                            .where(Proxy.country == country, Proxy.in_use.is_(False))
                            .limit(1)
                        )
                        if not proxy:
                            raise ValueError(f"No free proxy for {country}")
                        proxy.account_id = account.id
                        proxy.in_use = True
                        session.add(
                            DepositAddress(
                                account_id=account.id,
                                chain=Chain.SOLANA,
                                address=deposit_address,
                            )
                        )
                        await session.commit()
                    successes.append(idx)
                except Exception as e:
                    from loguru import logger

                    logger.info(f"e: {e}")
                    failures.append(name or "")
    finally:
        os.remove(path)
    report = f"Импорт завершён. Успешно: {len(successes)}, Ошибок: {len(failures)}"
    if failures:
        failed_list = "\n".join(f"`{name}`" for name in failures)
        report = f"{report}\n" f"Не удалось добавить аккаунты:\n" f"{failed_list}"
    await message.answer(
        report, reply_markup=accounts_keyboard(), parse_mode="Markdown"
    )

    await state.clear()
    await state.update_data(exchange=exchange)
