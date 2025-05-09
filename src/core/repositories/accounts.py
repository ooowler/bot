from collections.abc import Iterable
from sqlalchemy import select, or_
from sqlalchemy.orm import joinedload

from src.exceptions import NoFreeProxy, ParentAccountNotFound
from src.constants import METRICS_DB_PREFIX
from src.core.clients.databases.postgres import pg
from src.core.clients.metrics import metrics
from src.core.models import Account, UserFriend, DepositAddress


from sqlalchemy import select, or_
from src.constants import METRICS_DB_PREFIX
from src.core.clients.databases.postgres import pg
from src.core.clients.metrics import metrics
from src.core.models import Account
from typing import Optional, Tuple, Dict
from sqlalchemy import select
from src.core.models import Proxy, FakeHeader, Account
from src.core.clients.databases.postgres import pg
from src.core.clients.exchanges.backpack.backpack import BackpackExchangeClient
from loguru import logger


@metrics.track(prefix=METRICS_DB_PREFIX)
async def fetch_accounts(
    owner_tids: list[int], with_friends: bool = False
) -> list[Account]:
    if with_friends:
        my_tid = owner_tids[0]
        friends = await confirmed_friends_with_username(my_tid)

        for tid, _ in friends:
            owner_tids.append(tid)

    async with pg.session_maker() as s:
        stmt = select(Account).where(Account.owner_tid.in_(owner_tids))
        return list(await s.scalars(stmt))


@metrics.track(prefix=METRICS_DB_PREFIX)
async def get_transfer_targets(
    owner_tid: int,
    from_acc_id: int,
    parent_id: int | None,
) -> list[Account]:
    """
    Возвращает список аккаунтов для перевода:
     - все sub-аккаунты (parent_id == from_acc_id)
     - и, если parent_id != None, сам parent (id == parent_id).
    Только среди owner_tid.
    """
    async with pg.session_maker() as s:
        # строим условие parent == from_acc_id или id == parent_id (если задано)
        if parent_id is not None:
            filter_expr = or_(
                Account.parent_id == from_acc_id,
                Account.id == parent_id,
            )
        else:
            filter_expr = Account.parent_id == from_acc_id

        stmt = (
            select(Account)
            .where(
                Account.owner_tid == owner_tid,
                filter_expr,
            )
            .order_by(Account.id)
        )
        return (await s.scalars(stmt)).all()


@metrics.track(prefix=METRICS_DB_PREFIX)
async def get_by_name(name: str) -> Account | None:
    """Найти аккаунт по уникальному name."""
    async with pg.session_maker() as s:
        stmt = select(Account).where(Account.name == name)
        return await s.scalar(stmt)


@metrics.track(prefix=METRICS_DB_PREFIX)
async def get_by_id(acc_id: int) -> Account | None:
    """Вернуть Account без связей."""
    async with pg.session_maker() as s:
        return await s.get(Account, acc_id)


@metrics.track(prefix=METRICS_DB_PREFIX)
async def get_deposit_address(acc_id: int) -> DepositAddress | None:
    """Вернуть первый DepositAddress для аккаунта."""
    async with pg.session_maker() as s:
        q = select(DepositAddress).where(DepositAddress.account_id == acc_id).limit(1)
        return await s.scalar(q)


# ───────── confirmed‑друзья ─────────
@metrics.track(prefix=METRICS_DB_PREFIX)
async def confirmed_friend_ids(user_tid: int) -> list[int]:
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


@metrics.track(prefix=METRICS_DB_PREFIX)
async def get_backpack_client_by_account_id(
    account_id: int,
) -> Optional[BackpackExchangeClient]:
    """
    Загружает аккаунт, активный прокси, fake headers и cookies для account_id и
    возвращает настроенный клиент BackpackExchangeClient.
    Если аккаунт не найден — возвращает None.
    """
    # получаем аккаунт
    async with pg.session_maker() as session:
        account = await session.scalar(select(Account).where(Account.id == account_id))
        if not account:
            logger.warning("Account %s not found", account_id)
            return None

        # proxy
        proxy_obj = await session.scalar(
            select(Proxy).where(
                Proxy.account_id == account_id,
                Proxy.in_use.is_(True),
            )
        )
        proxy_url = None
        if proxy_obj:
            proxy_url = (
                f"socks5://{proxy_obj.login}:{proxy_obj.password}@"
                f"{proxy_obj.ip}:{proxy_obj.port}"
            )
            logger.debug("Using proxy_url %s for account %s", proxy_url, account_id)

        # fake headers / cookies
        fake_obj = await session.scalar(
            select(FakeHeader).where(FakeHeader.account_id == account_id)
        )
        fake_headers = fake_obj.headers if fake_obj and fake_obj.headers else {}
        cookies = fake_obj.cookies if fake_obj and fake_obj.cookies else {}

    # создаём клиента
    client = BackpackExchangeClient(
        api_key=account.api_key,
        api_secret=account.api_secret,
        proxy_url=proxy_url,
        fake_headers=fake_headers,
        cookies=cookies,
    )
    return client
