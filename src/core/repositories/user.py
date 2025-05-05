from sqlalchemy import select

from src.constants import METRICS_DB_PREFIX
from src.core.clients.databases.postgres import pg
from src.core.clients.metrics import metrics
from src.core.models import User


@metrics.track(prefix=METRICS_DB_PREFIX)
async def ensure_user(tg_id: int, username: str | None) -> User:
    """Создаёт пользователя, если не существует, и возвращает объект User."""
    async with pg.session_maker() as s:
        user = await s.scalar(select(User).where(User.telegram_id == tg_id))
        if user:
            return user
        user = User(telegram_id=tg_id, username=username or "")
        s.add(user)
        await s.commit()
        return user


@metrics.track(prefix=METRICS_DB_PREFIX)
async def user_by_username(username: str) -> User | None:
    async with pg.session_maker() as s:
        return await s.scalar(select(User).where(User.username.ilike(username)))
