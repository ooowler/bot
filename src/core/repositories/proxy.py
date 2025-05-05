from sqlalchemy import delete, func, select

from src.constants import METRICS_DB_PREFIX
from src.core.clients.databases.postgres import pg
from src.core.clients.metrics import metrics
from src.core.models import Proxy

from collections.abc import Iterable


@metrics.track(prefix=METRICS_DB_PREFIX)
async def country_stats() -> list[tuple[str | None, int]]:
    """
    [(country, count), …]  – отсортировано по count убыванием.
    Country может быть None, если значение в БД пустое.
    """
    async with pg.session_maker() as session:
        result = await session.execute(
            select(Proxy.country, func.count())
            .group_by(Proxy.country)
            .order_by(func.count().desc())
        )
        return list(result.all())


@metrics.track(prefix=METRICS_DB_PREFIX)
async def count_available_by_country(country: str) -> int:
    """Сколько прокси не in_use для указанной страны."""
    async with pg.session_maker() as session:
        return await session.scalar(
            select(func.count())
            .select_from(Proxy)
            .where(Proxy.country == country, Proxy.in_use.is_(False))
        )


@metrics.track(prefix=METRICS_DB_PREFIX)
async def delete_available_by_country(country: str, limit: int) -> int:
    """
    Удаляет ≤ `limit` свободных прокси заданной страны.
    Возвращает фактически удалённое количество.
    """
    async with pg.session_maker() as session:
        ids = await session.scalars(
            select(Proxy.id)
            .where(Proxy.country == country, Proxy.in_use.is_(False))
            .limit(limit)
        )
        id_list: list[int] = list(ids.all())
        if not id_list:
            return 0

        await session.execute(delete(Proxy).where(Proxy.id.in_(id_list)))
        await session.commit()
        return len(id_list)


@metrics.track(prefix=METRICS_DB_PREFIX)
async def add_proxies(raw_lines: Iterable[str], country: str) -> list[Proxy]:
    """
    Принимает коллекцию строк вида  ip:port:login:pass  и страну.
    Валидирует, вставляет в БД, возвращает список созданных ORM‑объектов.
    Некорректные строки пропускает.
    """
    objs: list[Proxy] = []
    for raw in raw_lines:
        parts = raw.split(":")
        if len(parts) != 4:
            continue
        host, port, login, password = parts
        try:
            port_int = int(port)
        except ValueError:
            continue
        objs.append(
            Proxy(
                ip=host,
                port=port_int,
                login=login,
                password=password,
                country=country,
            )
        )

    if not objs:
        return []

    async with pg.session_maker() as s:
        s.add_all(objs)
        await s.commit()
    return objs
