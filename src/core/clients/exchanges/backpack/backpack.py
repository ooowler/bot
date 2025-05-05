import base64
import json
import time
from typing import Any, Optional
from decimal import Decimal, ROUND_DOWN

from cryptography.hazmat.primitives.asymmetric import ed25519

from aiohttp_socks import ProxyConnector
from aiohttp import ClientTimeout, ClientSession
from aiohttp.client_exceptions import ServerDisconnectedError, ClientConnectorError
from loguru import logger
from sqlalchemy import select, update
from src.core.clients.exchanges.backpack.schemas import (
    BalancesResponse,
    BorrowLendPositionsResponse,
)
from src.core.models import Account, Proxy
from src.core.clients.databases.postgres import pg
from prometheus_client import Summary
import aiohttp
from cryptography.hazmat.primitives.asymmetric import ed25519
from aiohttp_socks import ProxyConnector
from aiohttp import ClientTimeout, ClientSession
from aiohttp.client_exceptions import ServerDisconnectedError, ClientConnectorError
from loguru import logger
from tenacity import (
    AsyncRetrying,
    RetryError,
    stop_after_attempt,
    wait_fixed,
    retry_if_exception_type,
)
from sqlalchemy import select, update
from prometheus_client import Summary, Counter

from src.core.models import Account, Proxy
from decimal import Decimal, ROUND_DOWN

REQUEST_LATENCY = Summary(
    "backpack_request_duration_seconds",
    "Время выполнения запроса к Backpack API",
    ["instruction", "method"],
)

REQUEST_COUNT = Counter(
    "backpack_request_total",
    "Количество запросов к Backpack API",
    ["instruction", "method"],
)


class BackpackExchangeClient:
    def __init__(
        self,
        api_key: str,
        api_secret: str,
        proxy_url: Optional[str] = None,
        fake_headers: Optional[dict] = None,
        cookies: Optional[dict] = None,
        base_url: str = "https://api.backpack.exchange/",
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
        self, instruction: str, timestamp: int, params: Optional[dict] = None
    ) -> dict:
        sorted_params = (
            {
                k: (str(v).lower() if isinstance(v, bool) else v)
                for k, v in sorted(params.items())
            }
            if params
            else {}
        )

        param_str = "&".join(f"{k}={v}" for k, v in sorted_params.items())
        sign_str = f"instruction={instruction}"
        if param_str:
            sign_str += f"&{param_str}"
        sign_str += f"&timestamp={timestamp}&window=5000"

        return base64.b64encode(self.private_key_obj.sign(sign_str.encode())).decode()

    async def _request_with_retry(
        self,
        send_func,
        *args,
        instruction: Optional[str] = None,
        method: Optional[str] = None,
        endpoint: Optional[str] = None,
        retries: int = 2,
    ) -> Any:
        """
        Утилита для исполнения запроса с retry через tenacity.
        """
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(retries),
            wait=wait_fixed(1),
            retry=retry_if_exception_type(
                (ServerDisconnectedError, ClientConnectorError)
            ),
            reraise=True,
        ):
            REQUEST_COUNT.labels(
                instruction=instruction or "", method=(method or "").upper()
            ).inc()
            with REQUEST_LATENCY.labels(
                instruction=instruction or "", method=(method or "").upper()
            ).time():
                try:
                    return await send_func(*args)
                except (ServerDisconnectedError, ClientConnectorError) as ex:
                    logger.error("Proxy failure on {} {}: {}", method, endpoint, ex)
                    await self.change_proxy()
                    raise

    async def _send_request(
        self,
        method: str,
        endpoint: str,
        instruction: str,
        params: Optional[dict] = None,
        need_response: bool = True,
    ) -> Any:
        url = f"{self.base_url}{endpoint}"
        data = json.dumps(params) if method.upper() in ("POST", "PATCH") else None

        async def _inner():
            headers = {
                "X-API-Key": self.api_key,
                "X-Signature": self._generate_signature(
                    instruction, int(time.time() * 1000), params
                ),
                "X-Timestamp": str(int(time.time() * 1000)),
                "X-Window": "5000",
                "Content-Type": "application/json; charset=utf-8",
                **self.fake_headers,
            }
            connector = (
                ProxyConnector.from_url(self.proxy_url) if self.proxy_url else None
            )
            timeout = ClientTimeout(total=30)
            async with ClientSession(connector=connector, timeout=timeout) as session:
                async with session.request(
                    method=method.upper(),
                    url=url,
                    headers=headers,
                    params=None if data else params,
                    data=data,
                    cookies=self.cookies,
                ) as resp:
                    text = await resp.text()
                    if not need_response:
                        return None
                    return json.loads(text)

        try:
            return await self._request_with_retry(
                _inner, instruction=instruction, method=method, endpoint=endpoint
            )
        except RetryError as e:
            logger.error("Max retries reached for {} {}: {}", method, endpoint, e)
            return {"error": "proxy_failure", "message": str(e)}
        except json.JSONDecodeError:
            logger.error("Invalid JSON from {}: {}", url, await resp.text())
            return {"error": "invalid_json"}
        except Exception as e:
            logger.exception("Unhandled error: %s", e)
            return {"error": "unexpected", "message": str(e)}

    async def send_public_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict] = None,
    ) -> Any:
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            **self.fake_headers,
        }

        async def _inner_public():
            connector = (
                ProxyConnector.from_url(self.proxy_url) if self.proxy_url else None
            )
            timeout = ClientTimeout(total=30)
            async with ClientSession(connector=connector, timeout=timeout) as session:
                async with session.request(
                    method=method.upper(),
                    url=url,
                    headers=headers,
                    params=params,
                    cookies=self.cookies,
                ) as resp:
                    text = await resp.text()
                    return json.loads(text)

        try:
            return await self._request_with_retry(
                _inner_public, instruction="public", method=method, endpoint=endpoint
            )
        except RetryError as e:
            logger.error(
                "Max retries reached for public {} {}: {}", method, endpoint, e
            )
            return {"error": "proxy_failure", "message": str(e)}

    async def get_balance(self) -> BalancesResponse:
        response = await self._send_request(
            method="GET",
            endpoint="api/v1/capital",
            instruction="balanceQuery",
        )
        return BalancesResponse(balances=response)

    async def get_borrow_lend_positions(self) -> BorrowLendPositionsResponse:
        "https://api.backpack.exchange/api/v1/borrowLend/positions"
        response = await self._send_request(
            method="GET",
            endpoint="api/v1/borrowLend/positions",
            instruction="borrowLendPositionQuery",
        )
        return BorrowLendPositionsResponse(positions=response)

    async def request_withdrawal(
        self,
        address: str,
        blockchain: str,
        symbol: str,
        quantity: str,
        two_factor_token: Optional[str] = None,
        client_id: Optional[str] = None,
        auto_borrow: bool = False,
        auto_lend_redeem: bool = False,
    ) -> dict:
        params = {
            "address": address,
            "blockchain": blockchain,
            "symbol": symbol,
            "quantity": quantity,
            "autoBorrow": auto_borrow,
            "autoLendRedeem": auto_lend_redeem,
        }

        if two_factor_token:
            params["twoFactorToken"] = two_factor_token
        if client_id:
            params["clientId"] = client_id

        return await self._send_request(
            method="POST",
            endpoint="wapi/v1/capital/withdrawals",
            instruction="withdraw",
            params=params,
        )

    async def create_order(
        self,
        symbol: str,
        side: str,  # "Ask" (sell) or "Bid" (buy)
        quantity: str,
        order_type: str,  # "Limit" or "Market"
        price: Optional[str] = None,
    ) -> dict:
        if order_type == "Limit" and not price:
            raise ValueError("Price is required for Limit orders")

        params = {
            "symbol": symbol,
            "side": side,
            "orderType": order_type,
            "quantity": quantity,
            "autoBorrow": False,
            "autoBorrowRepay": False,
            "autoLend": False,
            "autoLendRedeem": False,
            "reduceOnly": False,
        }

        if order_type == "Limit":
            params["price"] = price
            params["timeInForce"] = "GTC"  # good till canceled
            params["postOnly"] = False

        return await self._send_request(
            method="POST",
            endpoint="api/v1/order",
            instruction="orderExecute",
            params=params,
        )

    async def convert_all_to_usdc(self, order_type: str = "Limit") -> list[dict]:
        results = []

        balance = await self.get_balance()
        positions = await self.get_borrow_lend_positions()
        tickers = await self.get_all_tickers()
        symbols = {t["symbol"] for t in tickers}

        # Словарь netQuantity из позиций
        net_quantities = {
            p["symbol"].replace("_USDC", ""): float(p.get("netQuantity", 0))
            for p in positions
            if isinstance(p.get("netQuantity"), str)
        }

        for token, data in balance.items():
            available = Decimal(data["available"])
            net_quantity = Decimal(str(net_quantities.get(token, 0)))
            total_quantity = available + net_quantity

            if token == "USDC" or total_quantity <= 0:
                continue

            symbol = f"{token}_USDC"
            if symbol not in symbols:
                results.append({"token": token, "status": "no_usdc_pair"})
                continue

            try:
                if order_type == "Limit":
                    orderbook = await self.get_order_book_depth(symbol)
                    asks = orderbook.get("asks", [])
                    if not asks:
                        results.append({"token": token, "status": "no_asks"})
                        continue

                    price_str = asks[0][0]
                    quantity_format_sample = asks[0][1]

                    price = Decimal(price_str)
                    price_precision = abs(Decimal(price_str).as_tuple().exponent)
                    quantity_precision = abs(
                        Decimal(quantity_format_sample).as_tuple().exponent
                    )

                    rounded_quantity = str(
                        total_quantity.quantize(
                            Decimal(f"1e-{quantity_precision}"), rounding=ROUND_DOWN
                        )
                    )
                    rounded_price = str(
                        price.quantize(
                            Decimal(f"1e-{price_precision}"), rounding=ROUND_DOWN
                        )
                    )

                    order = await self.create_order(
                        symbol=symbol,
                        side="Ask",
                        quantity=rounded_quantity,
                        order_type="Limit",
                        price=rounded_price,
                    )
                else:
                    order = await self.create_order(
                        symbol=symbol,
                        side="Ask",
                        quantity=str(total_quantity),
                        order_type="Market",
                    )

                if "error" in order:
                    results.append(
                        {
                            "token": token,
                            "pair": symbol,
                            "quantity": float(total_quantity),
                            "status": "failed",
                            "order_type": order_type,
                            "error_detail": order,
                        }
                    )
                else:
                    results.append(
                        {
                            "token": token,
                            "pair": symbol,
                            "quantity": float(total_quantity),
                            "status": "order_placed",
                            "order_type": order_type,
                            "order_id": order.get("id"),
                        }
                    )

            except Exception as e:
                results.append(
                    {
                        "token": token,
                        "pair": symbol,
                        "quantity": float(total_quantity),
                        "status": "error",
                        "error": str(e),
                    }
                )

        return results

    async def get_open_orders(
        self,
        symbol: Optional[str] = None,
        market_type: Optional[str] = "SPOT",
    ) -> list[dict]:
        params = {}
        if symbol:
            params["symbol"] = symbol
        if market_type:
            params["marketType"] = market_type

        return await self._send_request(
            method="GET",
            endpoint="api/v1/orders",
            instruction="orderQueryAll",
            params=params,
        )

    async def get_open_positions(self) -> list[dict]:
        return await self._send_request(
            method="GET", endpoint="api/v1/position", instruction="positionQuery"
        )

    async def close_all_perp_positions(self) -> dict:
        positions = await self.get_open_positions()
        closed_count = 0
        failed = []

        for position in positions:
            symbol = position["symbol"]
            net_qty = float(position["netQuantity"])

            if net_qty == 0:
                continue

            side = (
                "Bid" if net_qty < 0 else "Ask"
            )  # To close short -> buy (Bid), to close long -> sell (Ask)
            quantity = str(abs(net_qty))

            try:
                response = await self.create_order(
                    symbol=symbol, side=side, quantity=quantity, order_type="Market"
                )
                if response.get("id"):
                    closed_count += 1
                else:
                    failed.append({"symbol": symbol, "error": response})
            except Exception as e:
                failed.append({"symbol": symbol, "error": str(e)})

        return {"closed": closed_count, "total": len(positions), "failed": failed}

    async def get_account_info(self) -> dict:
        return await self._send_request(
            method="GET",
            endpoint="api/v1/account",
            instruction="accountQuery",
        )

    async def update_account_settings(
        self,
        auto_borrow_settlements: bool = True,
        auto_lend: bool = True,
        auto_repay_borrows: bool = True,
        leverage_limit: Optional[str | int] = None,
    ) -> dict:
        payload = {
            "autoBorrowSettlements": auto_borrow_settlements,
            "autoLend": auto_lend,
            "autoRepayBorrows": auto_repay_borrows,
        }
        if leverage_limit:
            payload["leverageLimit"] = str(leverage_limit)

        return await self._send_request(
            method="PATCH",
            endpoint="api/v1/account",
            instruction="accountUpdate",
            params=payload,
            need_response=False,
        )

    async def buy_token_with_stables(self, symbol: str, percent: float = 100.0) -> dict:
        if not symbol.endswith("_USDC"):
            return {"error": "symbol must end with _USDC"}

        token = "USDC"
        balance = await self.get_balance()
        positions = await self.get_borrow_lend_positions()

        # Получаем netQuantity по USDC в лендинге
        net_quantity = Decimal("0")
        for p in positions:
            if p.get("symbol") == "USDC":
                try:
                    net_quantity = Decimal(p.get("netQuantity", 0))
                except:
                    net_quantity = Decimal("0")

        usdc_available = Decimal(balance.get("USDC", {}).get("available", 0))
        total_usdc = usdc_available + net_quantity

        if total_usdc <= 0:
            return {"error": "no USDC balance"}

        amount_to_spend = total_usdc * Decimal(percent) / Decimal(100)

        # Получаем стакан по символу
        orderbook = await self.get_order_book_depth(symbol)
        asks = orderbook.get("asks", [])
        if not asks:
            return {"error": "no asks in orderbook"}

        price = Decimal(asks[0][0])
        quantity_sample = asks[0][1]
        quantity_precision = abs(Decimal(quantity_sample).as_tuple().exponent)

        quantity = (amount_to_spend / price).quantize(
            Decimal(f"1e-{quantity_precision}"), rounding=ROUND_DOWN
        )

        order = await self.create_order(
            symbol=symbol, side="Bid", quantity=str(quantity), order_type="Market"
        )

        if "error" in order:
            return {"status": "failed", "details": order}

        return {
            "status": "order_placed",
            "symbol": symbol,
            "spent_usdc": float(amount_to_spend),
            "quantity": float(quantity),
            "order_id": order.get("id"),
        }

    async def get_balances_usd(self) -> list[dict]:
        balances = await self.get_balance()

        lend_positions = await self.get_borrow_lend_positions()
        net_qty = {p["symbol"]: Decimal(p["netQuantity"]) for p in lend_positions}

        tickers = await self.get_all_tickers()
        prices = {t["symbol"]: Decimal(t["lastPrice"]) for t in tickers}

        result: list[dict] = []
        for token, parts in balances.items():
            if token == "USDC":
                continue

            qty = Decimal(parts["available"]) + net_qty.get(token, Decimal("0"))
            if qty <= 0:
                continue

            pair = f"{token}_USDC"
            price = prices.get(pair) or prices.get(f"{pair}_PERP")
            if price is None:
                continue

            result.append(
                {
                    "token": token,
                    "quantity": float(qty),
                    "usd": float(qty * price),
                }
            )

        result.sort(key=lambda x: x["usd"], reverse=True)
        return result

    async def change_proxy(self) -> None:
        """
        Снимает флаг in_use у текущего прокси и назначает новый прокси
        (in_use=True, account_id=self.account_id) для этого клиента.
        """
        async with pg.session_maker() as session:
            # Найти аккаунт по api_key
            account = await session.scalar(
                select(Account).where(Account.api_key == self.api_key)
            )
            if not account:
                logger.warning("Не найден аккаунт для api_key=%s", self.api_key)
                return

            # Освободить старый прокси
            old_proxy = await session.scalar(
                select(Proxy).where(
                    Proxy.account_id == account.id, Proxy.in_use.is_(True)
                )
            )
            if old_proxy:
                await session.execute(
                    update(Proxy).where(Proxy.id == old_proxy.id).values(in_use=False)
                )
                logger.info(
                    "Освобождён старый прокси id=%s для аккаунта %s",
                    old_proxy.id,
                    account.id,
                )

            # Назначить новый прокси
            new_proxy = await session.scalar(
                select(Proxy)
                .where(
                    Proxy.in_use.is_(False),
                    Proxy.account_id.is_(None),
                    Proxy.country == account.country,  # при необходимости
                )
                .limit(1)
            )
            if not new_proxy:
                logger.error(
                    "Нет свободных прокси для назначения аккаунту %s", account.id
                )
                await session.commit()  # фиксируем освобождение старого, если было
                return

            await session.execute(
                update(Proxy)
                .where(Proxy.id == new_proxy.id)
                .values(account_id=account.id, in_use=True)
            )
            await session.commit()
            logger.info(
                "Назначен новый прокси id=%s для аккаунта %s", new_proxy.id, account.id
            )

    async def get_order_book_depth(self, symbol: str) -> dict:
        return await self.send_public_request(
            method="GET",
            endpoint="api/v1/depth",
            params={"symbol": symbol},
        )

    async def get_all_tickers(self) -> list[dict]:
        return await self.send_public_request(
            method="GET",
            endpoint="api/v1/tickers",
        )
