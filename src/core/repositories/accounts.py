from collections.abc import Iterable
from sqlalchemy import select, or_
from sqlalchemy.orm import joinedload

from src.exceptions import NoFreeProxy, ParentAccountNotFound
from src.constants import METRICS_DB_PREFIX
from src.core.clients.databases.postgres import pg
from src.core.clients.metrics import metrics
from src.core.models import Account, UserFriend


# ───────── базовый выбор аккаунтов ─────────
@metrics.track(prefix=METRICS_DB_PREFIX)
async def fetch_accounts(owner_tids: Iterable[int]) -> list[Account]:
    """Все аккаунты, у которых owner_tid ∈ owner_tids."""
    async with pg.session_maker() as s:
        stmt = select(Account).where(Account.owner_tid.in_(owner_tids))
        return list(await s.scalars(stmt))


# ───────── confirmed‑друзья ─────────
@metrics.track(prefix=METRICS_DB_PREFIX)
async def confirmed_friend_ids(user_tid: int) -> list[int]:
    """ID всех подтверждённых друзей пользователя."""
    async with pg.session_maker() as s:
        return list(
            await s.scalars(
                select(UserFriend.friend_id).where(
                    (UserFriend.user_id == user_tid) & (UserFriend.confirmed.is_(True))
                )
            )
        )


@metrics.track(prefix=METRICS_DB_PREFIX)
async def confirmed_friends_with_username(
    user_tid: int,
) -> list[tuple[int, str | None]]:
    """
    [(friend_tid, username_or_None), …] с eager‑load username,
    чтобы после закрытия сессии доступа к БД не требовалось.
    """
    async with pg.session_maker() as s:
        links = await s.scalars(
            select(UserFriend)
            .options(joinedload(UserFriend.friend))
            .where((UserFriend.user_id == user_tid) & (UserFriend.confirmed.is_(True)))
        )
        return [
            (l.friend_id, l.friend.username) for l in links  # type: ignore[union-attr]
        ]


@metrics.track(prefix=METRICS_DB_PREFIX)
async def get_by_api_or_name(key_or_name: str) -> Account | None:
    """
    Найти аккаунт по точному совпадению `api_key` **или** `name`.
    """
    async with pg.session_maker() as s:
        stmt = select(Account).where(
            or_(Account.api_key == key_or_name, Account.name == key_or_name)
        )
        return await s.scalar(stmt)


@metrics.track(prefix=METRICS_DB_PREFIX)
async def delete_by_api_or_name(ident: str) -> Account | None:
    """
    Удаляет аккаунт по точному совпадению `api_key` **или** `name`.
    Возвращает удалённый ORM‑объект, либо None, если не найден.
    """
    async with pg.session_maker() as s:
        acc = await s.scalar(
            select(Account).where(or_(Account.api_key == ident, Account.name == ident))
        )
        if not acc:
            return None
        await s.delete(acc)
        await s.commit()
        return acc


@metrics.track(prefix=METRICS_DB_PREFIX)
async def get_by_id(acc_id: int) -> Account | None:
    """Вернуть аккаунт по ID или None, если не найден."""
    async with pg.session_maker() as s:
        return await s.get(Account, acc_id)


from src.core.models import Account, FakeHeader, Proxy, DepositAddress


@metrics.track(prefix=METRICS_DB_PREFIX)
async def add_account_full(
    *,
    account: Account,
    fake_header: FakeHeader,
    deposit: DepositAddress,
) -> Proxy:
    """
    Сохраняет переданные ORM‑объекты, находит свободный Proxy.
    • account, fake_header, deposit должны быть НЕ сохранены ранее.
    • Связь выставляется здесь (fake_header.account = account и т.д.).
    • Возвращает выделенный Proxy или бросает NoFreeProxy.
    """
    async with pg.session_maker() as s:
        # 1) account
        s.add(account)
        await s.flush()  # account.id гарантирован

        # 2) связать дочерние модели
        fake_header.account_id = account.id
        deposit.account_id = account.id
        s.add_all([fake_header, deposit])

        # 3) взять proxy
        proxy = await s.scalar(
            select(Proxy)
            .where(Proxy.country == account.country, Proxy.in_use.is_(False))
            .limit(1)
        )
        if not proxy:
            raise NoFreeProxy(account.country)

        proxy.account_id = account.id
        proxy.in_use = True

        await s.commit()
        return proxy


@metrics.track(prefix=METRICS_DB_PREFIX)
async def get_parent_id(ident: str) -> int:
    """Вернёт id родительского аккаунта по api_key/имени или бросит ParentAccountNotFound."""
    parent = await get_by_api_or_name(ident)
    if parent is None:
        raise ParentAccountNotFound(ident)
    return parent.id
