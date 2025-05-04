from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy import select, literal, BigInteger
from src.bot.triggers import Texts
from src.bot.features.accounts.keyboards import accounts_keyboard
from src.core.clients.databases.postgres import pg
from src.core.models import Account, UserFriend

router = Router()


@router.message(F.text == Texts.Accounts.STATS)
async def accounts_stats(message: Message):
    my_tid = message.from_user.id  # ваш Telegram‑ID

    async with pg.session_maker() as session:
        friend_ids_subq = select(UserFriend.friend_id).where(
            UserFriend.user_id == literal(my_tid, type_=BigInteger)
        )

        allowed_ids_subq = friend_ids_subq.union_all(
            select(literal(my_tid, type_=BigInteger))
        ).subquery()

        accounts = (
            (
                await session.execute(
                    select(Account).where(
                        Account.owner_tid.in_(select(allowed_ids_subq))
                    )
                )
            )
            .scalars()
            .all()
        )

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
