import csv
import os
import random
from faker import Faker
from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger

from src.bot.features.accounts.keyboards import accounts_keyboard
from src.bot.features.accounts.states import AccountsStates
from src.bot.triggers import Texts
from src.core.models import Account, FakeHeader, DepositAddress, Chain
from src.core.repositories import accounts as accounts_repo
from src.exceptions import NoFreeProxy
from src.core.repositories.accounts import ParentAccountNotFound

router = Router()
_fake = Faker()


def _gen_headers() -> dict[str, str]:
    return {
        "User-Agent": _fake.user_agent(),
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
    }


def _gen_cookies() -> dict[str, str]:
    names = ["sessionid", "csrftoken", "auth_token", "userid", "tracking", "cartid"]
    return {
        n: _fake.uuid4()
        for n in _fake.random.sample(names, k=_fake.random.randint(2, 5))
    }


# ───────── старт импорта ─────────
@router.message(F.text == Texts.Accounts.ADD_CSV)
async def import_start(message: Message, state: FSMContext) -> None:
    await state.set_state(AccountsStates.import_csv)
    await message.answer(
        "Пришлите CSV‑файл (NAME,API_KEY,API_SECRET,COUNTRY,SOL_DEPOSIT_ADDRESS,PARENT):",
        reply_markup=accounts_keyboard(),
    )


# ───────── приём файла ─────────
@router.message(StateFilter(AccountsStates.import_csv), F.document)
async def import_csv(message: Message, state: FSMContext) -> None:
    file = message.document
    if not file.file_name.lower().endswith(".csv"):
        await message.answer(
            "Неверный формат файла, нужен CSV.", reply_markup=accounts_keyboard()
        )
        return

    exchange = (await state.get_data())["exchange"]
    path = f"/tmp/{file.file_unique_id}.csv"
    await message.bot.download(file, destination=path)

    successes: list[str] = []
    failures: list[str] = []

    try:
        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            reader.fieldnames = [h.strip().upper() for h in reader.fieldnames]

            for idx, row in enumerate(reader, 1):
                name = row.get("NAME", "").strip()
                try:
                    api_key = row["API_KEY"].strip()
                    api_secret = row["API_SECRET"].strip()
                    country = row["COUNTRY"].strip().upper()
                    deposit_address = row["SOL_DEPOSIT_ADDRESS"].strip()
                    parent_ident = row.get("PARENT", "").strip() or None

                    parent_id = None
                    if parent_ident:
                        parent_id = await accounts_repo.get_parent_id(parent_ident)

                    # формируем объекты
                    account = Account(
                        name=name,
                        api_key=api_key,
                        api_secret=api_secret,
                        exchange=exchange,
                        country=country,
                        parent_id=parent_id,
                        owner_tid=message.from_user.id,
                    )
                    fake_header = FakeHeader(
                        headers=_gen_headers(), cookies=_gen_cookies()
                    )
                    deposit = DepositAddress(
                        chain=Chain.SOLANA, address=deposit_address
                    )

                    await accounts_repo.add_account_full(
                        account=account,
                        fake_header=fake_header,
                        deposit=deposit,
                    )
                    successes.append(name)
                except (NoFreeProxy, ParentAccountNotFound, KeyError, ValueError) as e:
                    logger.warning(f"row {idx} failed: {e}")
                    failures.append(name or f"row#{idx}")
                except Exception as e:
                    failures.append(name or f"row#{idx}")
    finally:
        os.remove(path)

    report = (
        f"Импорт завершён.\n"
        f"✅ Успешно: {len(successes)}\n"
        f"❌ Ошибок: {len(failures)}"
    )
    if failures:
        report += "\nНе удалось загрузить:\n" + "\n".join(f"`{n}`" for n in failures)

    await message.answer(
        report, reply_markup=accounts_keyboard(), parse_mode="Markdown"
    )
    await state.clear()
