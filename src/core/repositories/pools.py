from sqlalchemy import select, delete
from src.constants import METRICS_DB_PREFIX
from src.core.clients.databases.postgres import pg
from src.core.clients.metrics import metrics

from src.core.models.pool import Pool, PoolAccountLink, PoolStatus
from src.core.models.user import User
from src.core.models import Account


@metrics.track(prefix=METRICS_DB_PREFIX)
async def get_active_pools() -> list[Pool]:
    """
    Возвращает все активные пулы (is_active=True).
    """
    async with pg.session_maker() as session:
        result = await session.scalars(select(Pool).where(Pool.is_active.is_(True)))
        return result.all()


@metrics.track(prefix=METRICS_DB_PREFIX)
async def create_pool(
    label: str,
    owner_telegram_id: int,
    settings: dict | None = None,
) -> Pool:
    """
    Создаёт новый пул для пользователя по telegram_id.
    Ищет внутренний User по telegram_id, затем сохраняет его id как owner_id.
    """
    async with pg.session_maker() as session:
        # найти internal User.id
        user = await session.scalar(
            select(User).where(User.telegram_id == owner_telegram_id)
        )
        if not user:
            raise LookupError(f"User with tg_id={owner_telegram_id} not found")
        pool = Pool(
            label=label,
            owner_id=user.id,
            settings=settings or {},
            is_active=True,
            status=PoolStatus.RUNNING.value,
        )
        session.add(pool)
        await session.commit()
        await session.refresh(pool)
        return pool


@metrics.track(prefix=METRICS_DB_PREFIX)
async def add_account_to_pool(pool_id: int, account_id: int) -> None:
    """
    Добавляет аккаунт в пул.
    """
    async with pg.session_maker() as session:
        link = PoolAccountLink(pool_id=pool_id, account_id=account_id)
        session.add(link)
        await session.commit()


@metrics.track(prefix=METRICS_DB_PREFIX)
async def remove_account_from_pool(pool_id: int, account_id: int) -> None:
    """
    Удаляет связь аккаунт-пул.
    """
    async with pg.session_maker() as session:
        await session.execute(
            delete(PoolAccountLink).where(
                PoolAccountLink.pool_id == pool_id,
                PoolAccountLink.account_id == account_id,
            )
        )
        await session.commit()


@metrics.track(prefix=METRICS_DB_PREFIX)
async def list_pools_for_user(owner_id: int) -> list[Pool]:
    """
    Возвращает все пулы пользователя, указанного по telegram_id.
    """
    async with pg.session_maker() as session:
        # найти internal User.id
        user = await session.scalar(select(User).where(User.telegram_id == owner_id))
        if not user:
            return []
        result = await session.scalars(select(Pool).where(Pool.owner_id == user.id))
        return result.all()


@metrics.track(prefix=METRICS_DB_PREFIX)
async def list_pool_accounts(pool_id: int) -> list[Account]:
    """
    Возвращает список всех Account, привязанных к пулу.
    """
    async with pg.session_maker() as session:
        result = await session.scalars(
            select(Account)
            .join(
                PoolAccountLink,
                Account.id == PoolAccountLink.account_id,
            )
            .where(PoolAccountLink.pool_id == pool_id)
        )
        return result.all()
