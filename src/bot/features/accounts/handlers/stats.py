from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy import select
from src.bot.triggers import Texts
from src.bot.features.accounts.keyboards import accounts_keyboard
from src.core.clients.databases.postgres import pg
from src.core.models import Account

router = Router()


@router.message(F.text == Texts.Accounts.STATS)
async def accounts_stats(message: Message):
    async with pg.session_maker() as session:
        accounts = (await session.execute(select(Account))).scalars().all()

    total_accounts = len(accounts)
    total_subaccounts = len([acc for acc in accounts if acc.parent_id])
    countries = sorted({acc.country for acc in accounts if acc.country})
    exchanges = sorted({acc.exchange for acc in accounts if acc.exchange})
    dates = [acc.created_at for acc in accounts if acc.created_at]
    earliest = min(dates) if dates else None
    latest = max(dates) if dates else None
    text = (
        f"📊 Статистика аккаунтов:\n"
        f"Всего аккаунтов: {total_accounts}\n"
        f"Всего субаккаунтов: {total_subaccounts}\n"
        f"Страны: {', '.join(countries) if countries else '—'}\n"
        f"Биржи: {', '.join(exchanges) if exchanges else '—'}\n"
    )
    if earliest:
        text += f"Первый аккаунт: {earliest:%Y-%m-%d}\n"
    if latest:
        text += f"Последний аккаунт: {latest:%Y-%m-%d}"
    await message.answer(text, reply_markup=accounts_keyboard())
