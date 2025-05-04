from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy import select, literal, BigInteger
from src.bot.triggers import Texts
from src.bot.features.accounts.keyboards import accounts_keyboard
from src.core.clients.databases.postgres import pg
from src.core.models import Account, UserFriend
from sqlalchemy.orm import aliased

router = Router()


@router.message(F.text == Texts.Accounts.STATS)
async def accounts_stats(message: Message):
    my_tid = message.from_user.id  # ваш Telegram‑ID

    async with pg.session_maker() as session:
        UF = aliased(UserFriend)

        stmt = (
            select(Account)
            .join(
                UF,
                (UF.user_id == my_tid) & (UF.friend_id == Account.owner_tid),
                isouter=True,
            )
            .where((Account.owner_tid == my_tid) | (UF.user_id.is_not(None)))
        )
        accounts = (await session.execute(stmt)).scalars().all()

    total = len(accounts)
    subs = sum(1 for a in accounts if a.parent_id)
    countries = sorted({a.country for a in accounts if a.country})
    exchanges = sorted({a.exchange for a in accounts if a.exchange})
    dates = [a.created_at for a in accounts if a.created_at]
    earliest = min(dates) if dates else None
    latest = max(dates) if dates else None

    lines = [
        "📊 Статистика аккаунтов (ваши + друзей):",
        f"Всего аккаунтов: {total}",
        f"Всего субаккаунтов: {subs}",
        f"Страны: {', '.join(countries) or '—'}",
        f"Биржи: {', '.join(exchanges) or '—'}",
    ]
    if earliest:
        lines.append(f"Первый аккаунт: {earliest:%Y-%m-%d}")
    if latest:
        lines.append(f"Последний аккаунт: {latest:%Y-%m-%d}")

    await message.answer("\n".join(lines), reply_markup=accounts_keyboard())
