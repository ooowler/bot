import os
import redis.asyncio as aioredis
from functools import cached_property

REDIS_APP_URL = os.getenv("REDIS_APP_URL")


class RedisClient:
    def __init__(self, url: str = REDIS_APP_URL) -> None:
        self._url = url

    @cached_property
    def client(self) -> aioredis.Redis:
        return aioredis.from_url(self._url, encoding="utf-8", decode_responses=True)

    async def ping(self) -> bool:
        return await self.client.ping()


redis = RedisClient()
