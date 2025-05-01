import redis.asyncio as aioredis
from functools import cached_property
from typing import Optional, Union

from src.settings import REDIS_APP_URL


class RedisClient:
    def __init__(self, url) -> None:
        self._url = url

    @cached_property
    def client(self) -> aioredis.Redis:
        return aioredis.from_url(self._url, encoding="utf-8", decode_responses=True)

    async def ping(self) -> bool:
        return await self.client.ping()

    async def set(
        self, key: str, value: Union[str, bytes], ttl: Optional[int] = None
    ) -> bool:
        return await self.client.set(name=key, value=value, ex=ttl)

    async def get(self, key: str) -> Optional[str]:
        return await self.client.get(name=key)

    async def delete(self, key: str) -> int:
        return await self.client.delete(key)


redis = RedisClient(url=REDIS_APP_URL)
