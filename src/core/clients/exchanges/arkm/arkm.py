import random
import base64
import hmac
import hashlib
import time
import json
from typing import Optional, Dict, Any
from aiohttp import ClientSession, ClientTimeout
from pydantic import BaseModel, ConfigDict, root_validator
import uuid
from aiohttp_socks import ProxyConnector
from aiohttp import ClientSession, ClientTimeout
from pydantic import Field


class ArkmExchangeClient:
    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = "https://arkm.com/api",
        account_id: Optional[int] = None,
        proxy_url: Optional[str] = None,
        fake_headers: Optional[Dict[str, Any]] = None,
        cookies: Optional[Dict[str, Any]] = None,
        volume: int = 0,
    ):
        self.base_url = base_url
        self.api_key = api_key
        self.api_secret = api_secret
        self.account_id = account_id
        self.proxy_url = proxy_url
        self.fake_headers = fake_headers or {}
        self.cookies = cookies or {}
        self.volume = volume

    def _generate_signature(
        self, method: str, request_path: str, body: str
    ) -> Dict[str, str]:
        expires = f"{int(time.time()) + 300}000000"
        hmac_key = base64.b64decode(self.api_secret).hex()
        signature_base = f"{self.api_key}{expires}{method}{request_path}{body}"
        digest = hmac.new(
            bytes.fromhex(hmac_key), signature_base.encode(), hashlib.sha256
        ).digest()
        signature = base64.b64encode(digest).decode()
        return {
            "Arkham-Api-Key": self.api_key,
            "Arkham-Expires": expires,
            "Arkham-Signature": signature,
        }

    async def request(
        self, method: str, request_path: str, body: Optional[dict] = None
    ) -> dict:
        body_str = (
            "" if method.lower() == "get" else json.dumps(body, separators=(",", ":"))
        )
        headers = {
            **self.fake_headers,
            **self._generate_signature(method, request_path, body_str),
            "Content-Type": "application/json",
        }
        url = f"{self.base_url}{request_path}"

        # создаём коннектор через aiohttp-socks, если есть proxy_url
        connector = ProxyConnector.from_url(self.proxy_url) if self.proxy_url else None

        async with ClientSession(
            connector=connector, timeout=ClientTimeout(total=3)
        ) as session:
            if method.lower() == "get":
                async with session.get(
                    url, headers=headers, cookies=self.cookies
                ) as resp:
                    resp.raise_for_status()
                    return await resp.json()
            elif method.lower() == "post":
                from loguru import logger

                logger.info(
                    f"url: {url}\nheaders: {headers}\n data: {body_str}\n cookies: {self.cookies}"
                )
                async with session.post(
                    url, headers=headers, data=body_str, cookies=self.cookies
                ) as resp:
                    resp.raise_for_status()
                    return await resp.json()
            else:
                raise ValueError(f"Unsupported HTTP method: {method.upper()}")

    async def order(
        self,
        action: str,  # "buy" или "sell"
        symbol: str,  # например "ARKM"
        quantity: float,  # объём
    ) -> dict:
        """
        Выставляем только market-ордер через простой эндпоинт.
        POST /orders/new/simple
        """
        body = {
            "side": action.lower(),  # "buy" или "sell"
            "size": str(quantity),  # строка
            "subaccountId": 0,  # ваш subaccount
            "symbol": f"{symbol.upper()}_USDT",  # например "ARKM_USDT"
        }
        return await self.request(
            method="POST",
            request_path="/orders/new/simple",
            body=body,
        )

    async def check_proxy(self) -> dict:
        url = "https://ipinfo.io/json"
        async with ClientSession(timeout=ClientTimeout(total=3)) as session:
            try:
                async with session.get(
                    url,
                    headers=self.fake_headers,
                    proxy=self.proxy_url,
                    cookies=self.cookies,
                ) as resp:
                    resp.raise_for_status()
                    return await resp.json()
            except Exception as e:
                raise RuntimeError(f"Ошибка проверки прокси: {e}")

    async def get_balance(self) -> dict:
        return await self.request("GET", "/account/balances")

    async def get_volumes(self) -> tuple[int, int]:
        return await self.request("GET", "/affiliate-dashboard/trading-volume-stats")

    async def get_token_price(self, token: str) -> float:
        data = await self.request("GET", f"/public/ticker?symbol={token}_USDT")
        return float(data.get("price", 0))
