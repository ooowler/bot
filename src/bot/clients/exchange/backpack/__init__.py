import base64
import json
import time
from typing import Any, Optional, Dict

import aiohttp
from cryptography.hazmat.primitives.asymmetric import ed25519
from src.bot.clients.exchange.backpack.schemas.balance import BalanceResponse, TokenBalance

class BackpackExchangeClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        api_secret: str,
        proxy_url: Optional[str] = None,
        fake_headers: Optional[dict] = None,
        cookies: Optional[dict] = None,
    ):
        self.base_url = base_url
        self.api_key = api_key
        self.api_secret = api_secret
        self.proxy_url = proxy_url
        self.fake_headers = fake_headers or {}
        self.cookies = cookies or {}

        self.private_key_obj = ed25519.Ed25519PrivateKey.from_private_bytes(
            base64.b64decode(api_secret)
        )

    def _generate_signature(
        self, action: str, timestamp: int, params: Optional[dict] = None
    ) -> dict:
        sorted_params = (
            {
                k: (str(v).lower() if isinstance(v, bool) else v)
                for k, v in sorted(params.items())
            }
            if params else {}
        )

        param_str = "&".join(f"{k}={v}" for k, v in sorted_params.items())
        sign_str = f"instruction={action}"
        if param_str:
            sign_str += f"&{param_str}"
        sign_str += f"&timestamp={timestamp}&window=5000"

        signature = base64.b64encode(
            self.private_key_obj.sign(sign_str.encode())
        ).decode()

        return {
            "X-API-Key": self.api_key,
            "X-Signature": signature,
            "X-Timestamp": str(timestamp),
            "X-Window": "5000",
            "Content-Type": "application/json; charset=utf-8",
            **self.fake_headers,
        }

    async def _send_request(
        self,
        method: str,
        endpoint: str,
        action: str,
        params: Optional[dict] = None,
    ) -> Any:
        url = f"{self.base_url}{endpoint}"
        timestamp = int(time.time() * 1000)
        headers = self._generate_signature(action, timestamp, params)
        data = json.dumps(params) if method.upper() in ("POST", "PATCH") else None

        async with aiohttp.ClientSession() as session:
            async with session.request(
                method=method.upper(),
                url=url,
                headers=headers,
                params=None if method.upper() in ("POST", "PATCH") else params,
                data=data,
                proxy=self.proxy_url,
                cookies=self.cookies,
            ) as resp:
                return await resp.json()

    async def get_balance(self) -> BalanceResponse:
        """
        Возвращает баланс в формате:
        BalanceResponse(balance={
            "BTC": TokenBalance(native=0.01, USD=500),
            ...
        })
        """
        response = await self._send_request(
            method="GET",
            endpoint="api/v1/capital",
            action="balanceQuery",
        )

        result = {}
        allowed_symbols = {"BTC", "ETH", "SOL", "USDC", "IO", "POINTS"}

        for symbol, data in response.items():
            if symbol not in allowed_symbols:
                continue
            native = float(data.get("available", 0))
            result[symbol] = TokenBalance(native=native, USD=0.0)  # USD можно рассчитать позже

        return BalanceResponse(balance=result)

