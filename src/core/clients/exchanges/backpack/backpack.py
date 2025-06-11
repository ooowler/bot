import asyncio
import base64
import json
import random
import time
from typing import Any, Optional
from decimal import Decimal, ROUND_DOWN
from datetime import datetime, timezone
from cryptography.hazmat.primitives.asymmetric import ed25519
import time as _time
from aiohttp import ClientSession, ClientTimeout
from aiohttp_socks import ProxyConnector
from aiohttp_socks import ProxyConnector
from aiohttp import ClientTimeout, ClientSession
from aiohttp.client_exceptions import ServerDisconnectedError, ClientConnectorError
from loguru import logger
from sqlalchemy import select, update
from src.core.clients.metrics import REQUEST_COUNT, REQUEST_LATENCY, metrics
from src.core.clients.exchanges.backpack.schemas import (
    AccountInfoResponse,
    BalancesResponse,
    BorrowLendPositionsResponse,
    ConvertAllToUsdcResponse,
    LimitOrderResponse,
    MarketOrderResponse,
    MarketSaleResult,
    OpenOrdersResponse,
    OrderResponseBase,
    Ticker,
    TickersResponse,
    TotalTokenQuantitiesResponse,
    WithdrawalResponse,
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

from src.core.models import Account, Proxy
from decimal import Decimal, ROUND_DOWN


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
        sign_str += f"&timestamp={timestamp}&window=60000"

        logger.info(f"sign_str: {sign_str}")
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
                    resp_json = await send_func(*args)
                    if isinstance(resp_json, dict) and resp_json.get("error"):
                        raise RuntimeError(f"API error: {resp_json.get('message')}")
                    return resp_json
                except (ServerDisconnectedError, ClientConnectorError) as ex:
                    logger.error("Proxy failure on {} {}: {}", method, endpoint, ex)
                    await self.change_proxy()
                    raise
                except Exception as ex:
                    logger.error("Unknown failure on {} {}: {}", method, endpoint, ex)
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
            _time = int(datetime.now(timezone.utc).timestamp() * 1000)
            headers = {
                "X-API-Key": self.api_key,
                "X-Signature": self._generate_signature(instruction, _time, params),
                "X-Timestamp": str(_time),
                "X-Window": "60000",
                "Content-Type": "application/json; charset=utf-8",
                **self.fake_headers,
            }
            connector = (
                ProxyConnector.from_url(self.proxy_url) if self.proxy_url else None
            )
            timeout = ClientTimeout(total=20)
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
        except json.JSONDecodeError as e:
            logger.error("Invalid JSON from {}: {}", url, e)
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

    @metrics.track("backpack")
    async def get_balance(self) -> BalancesResponse:
        response = await self._send_request(
            method="GET",
            endpoint="api/v1/capital",
            instruction="balanceQuery",
        )
        return BalancesResponse(balances=response)

    @metrics.track("backpack")
    async def get_borrow_lend_positions(self) -> BorrowLendPositionsResponse:
        response = await self._send_request(
            method="GET",
            endpoint="api/v1/borrowLend/positions",
            instruction="borrowLendPositionQuery",
        )
        return BorrowLendPositionsResponse(positions=response)

    @metrics.track("backpack")
    async def get_total_token_quantities(self) -> TotalTokenQuantitiesResponse:
        balances_resp, positions_resp = await asyncio.gather(
            self.get_balance(),
            self.get_borrow_lend_positions(),
        )
        totals = {
            symbol: tb.available + tb.locked + tb.staked
            for symbol, tb in balances_resp.balances.items()
        }

        for pos in positions_resp.positions:
            totals[pos.symbol] = (
                totals.get(pos.symbol, Decimal(0)) + pos.netExposureQuantity
            )

        return TotalTokenQuantitiesResponse(totals=totals)

    @metrics.track("backpack")
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

        data = await self._send_request(
            method="POST",
            endpoint="wapi/v1/capital/withdrawals",
            instruction="withdraw",
            params=params,
        )
        logger.info(f"data: {data}")

        return WithdrawalResponse(**data)

    @metrics.track("backpack")
    async def create_limit_order(
        self,
        symbol: str,
        side: str,  # Ask (=sell) | Bid (=buy)
        quantity: str,
        price: str,
    ) -> LimitOrderResponse:
        params = {
            "symbol": symbol,
            "side": side,
            "orderType": "Limit",
            "quantity": quantity,
            "price": price,
            "timeInForce": "GTC",
            "postOnly": False,
            "reduceOnly": False,
        }
        data = await self._send_request(
            method="POST",
            endpoint="api/v1/order",
            instruction="orderExecute",
            params=params,
        )
        return LimitOrderResponse(**data)

    @metrics.track("backpack")
    async def create_market_order(
        self,
        symbol: str,
        side: str,  # Ask (=sell) | Bid (=buy)
        quantity: str,
    ) -> MarketOrderResponse:
        params = {
            "symbol": symbol,
            "side": side,
            "orderType": "Market",
            "quantity": quantity,
            "autoLend": True,
            "autoLendRedeem": True,
            "autoBorrow": True,
            "autoBorrowRepay": True,
            # "reduceOnly": False,
        }
        data = await self._send_request(
            method="POST",
            endpoint="api/v1/order",
            instruction="orderExecute",
            params=params,
        )
        return MarketOrderResponse(**data)

    @metrics.track("backpack")
    async def convert_all_to_usdc(
        self,
    ) -> ConvertAllToUsdcResponse:
        precision_map: dict[str, int] = {
            "SOL": 2,
            "ETH": 4,
            "BTC": 5,
        }
        default_precision = 1

        totals = (await self.get_total_token_quantities()).totals

        symbols = []
        tasks = []
        for symbol, amount in totals.items():
            if symbol == "USDC" or amount <= 0:
                continue
            prec = precision_map.get(symbol, default_precision)
            quant = Decimal(f"1e-{prec}")
            quantized = amount.quantize(quant, rounding=ROUND_DOWN)
            if quantized <= 0:
                continue
            symbols.append(symbol)

            async def sell(sym: str, qty: Decimal) -> MarketOrderResponse:
                await asyncio.sleep(random.uniform(0, 5))
                return await self.create_market_order(
                    symbol=f"{sym}_USDC", side="Ask", quantity=str(qty)
                )

            tasks.append(sell(symbol, quantized))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        sale_results: list[MarketSaleResult] = []
        for sym, res in zip(symbols, results):
            if isinstance(res, MarketOrderResponse):
                sale_results.append(
                    MarketSaleResult(symbol=sym, success=True, order=res, error=None)
                )
            else:
                sale_results.append(
                    MarketSaleResult(
                        symbol=sym, success=False, order=None, error=str(res)
                    )
                )
        return ConvertAllToUsdcResponse(results=sale_results)

    @metrics.track("backpack")
    async def get_open_orders(
        self,
        market_type: str,
        symbol: str | None = None,
    ) -> OpenOrdersResponse:
        params: dict[str, Any] = {"marketType": market_type}
        if symbol:
            params["symbol"] = symbol

        data = await self._send_request(
            method="GET",
            endpoint="api/v1/orders",
            instruction="orderQueryAll",
            params=params,
        )
        orders = [OrderResponseBase(**o) for o in data]
        return OpenOrdersResponse(orders=orders)

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

    async def get_account_info(self) -> AccountInfoResponse:
        data = await self._send_request(
            method="GET",
            endpoint="api/v1/account",
            instruction="accountQuery",
        )
        return AccountInfoResponse(**data)

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

        await self._send_request(
            method="PATCH",
            endpoint="api/v1/account",
            instruction="accountUpdate",
            params=payload,
            need_response=False,
        )

    async def change_proxy(self) -> None:
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

    async def get_tickers(self) -> TickersResponse:
        data = await self.send_public_request(
            method="GET",
            endpoint="api/v1/tickers",
        )
        return TickersResponse(tickers=[Ticker(**item) for item in data])

    async def get_ticker(self, symbol) -> Ticker:
        data = await self.send_public_request(
            method="GET",
            endpoint=f"api/v1/ticker?symbol={symbol.upper()}",
        )
        return Ticker(**data)

    async def check_proxy(self) -> dict[str, Any]:
        start = _time.perf_counter()
        url = "https://ipinfo.io/json"
        connector = ProxyConnector.from_url(self.proxy_url) if self.proxy_url else None

        async with ClientSession(
            connector=connector,
            timeout=ClientTimeout(total=5),
        ) as session:
            async with session.get(
                url, headers=self.fake_headers, cookies=self.cookies
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()

        elapsed = _time.perf_counter() - start
        data["response_time"] = elapsed
        return data
