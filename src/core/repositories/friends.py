from sqlalchemy import select
from sqlalchemy.orm import joinedload

from src.constants import METRICS_DB_PREFIX
from src.core.clients.databases.postgres import pg
from src.core.clients.metrics import metrics
from src.core.models.user import User, UserFriend
from src.core.repositories.user import ensure_user, user_by_username


# ───────── список друзей ─────────
@metrics.track(prefix=METRICS_DB_PREFIX)
async def friends_for_user(tid: int) -> list[UserFriend]:
    async with pg.session_maker() as s:
        return list(
            await s.scalars(
                select(UserFriend)
                .options(joinedload(UserFriend.friend))
                .where(UserFriend.user_id == tid)
                .order_by(UserFriend.confirmed.desc())
            )
        )


# ───────── add / confirm ─────────
@metrics.track(prefix=METRICS_DB_PREFIX)
async def add_friend(
    me_tid: int,
    me_username: str | None,
    friend_username: str,
) -> tuple[bool, bool, User]:
    """
    Возвращает (уже_был, подтвержден_сейчас, friend_user).
    """
    friend = await user_by_username(friend_username)
    if not friend:
        raise LookupError("friend_not_found")
    if friend.telegram_id == me_tid:
        raise ValueError("self_add")

    async with pg.session_maker() as s:
        me = await ensure_user(me_tid, me_username)

        mine = await s.scalar(
            select(UserFriend).where(
                (UserFriend.user_id == me_tid)
                & (UserFriend.friend_id == friend.telegram_id)
            )
        )
        if mine:  # уже есть запись
            return True, mine.confirmed, friend

        reciprocal = await s.scalar(
            select(UserFriend).where(
                (UserFriend.user_id == friend.telegram_id)
                & (UserFriend.friend_id == me_tid)
            )
        )

        confirmed_now = bool(reciprocal)
        if reciprocal:
            reciprocal.confirmed = True

        s.add(
            UserFriend(
                user_id=me_tid,
                friend_id=friend.telegram_id,
                confirmed=confirmed_now,
            )
        )
        await s.commit()
        return False, confirmed_now, friend


# ───────── delete ─────────
@metrics.track(prefix=METRICS_DB_PREFIX)
async def delete_friend(me_tid: int, friend_username: str) -> tuple[bool, User | None]:
    """Удаляет дружбу и снимает confirmed у зеркальной записи."""
    async with pg.session_maker() as s:
        friend = await user_by_username(friend_username)
        if not friend:
            return False, None

        link = await s.scalar(
            select(UserFriend).where(
                (UserFriend.user_id == me_tid)
                & (UserFriend.friend_id == friend.telegram_id)
            )
        )
        if not link:
            return False, friend

        await s.delete(link)

        reciprocal = await s.scalar(
            select(UserFriend).where(
                (UserFriend.user_id == friend.telegram_id)
                & (UserFriend.friend_id == me_tid)
            )
        )
        if reciprocal:
            reciprocal.confirmed = False

        await s.commit()
        return True, friend
