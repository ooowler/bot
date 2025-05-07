#!/usr/bin/env python3
"""
Фоновый воркер для торговых пулов.
Каждый цикл:
  - Загружает все активные пулы.
  - Для каждого пула валидирует настройки через Pydantic.
  - Для каждого аккаунта в пуле:
      • Получает балансы и позиции borrow/lend через отдельные методы,
        пропуская аккаунт при валидационных ошибках.
      • Вычисляет net-баланс в USD.
      • Если список пуст — выполняет BUY по market.
      • Иначе — продаёт самый дорогой токен.
  - Ждёт минимальный interval среди всех пулов.
"""
import asyncio
from decimal import Decimal, InvalidOperation, ROUND_DOWN
from pydantic import BaseModel, Field, ValidationError
from types import SimpleNamespace
from prometheus_client import start_http_server, Summary, Counter

from src.core.repositories.pools import get_active_pools, list_pool_accounts
from src.core.clients.exchanges.backpack.backpack import BackpackExchangeClient

# Prometheus metrics
CYCLE_LATENCY = Summary(
    "pool_cycle_duration_seconds", "Duration of one full pool processing loop"
)
ORDER_COUNT = Counter(
    "pool_orders_executed_total",
    "Total number of orders executed",
    ["pool_id", "action"],
)
ERROR_COUNT = Counter(
    "pool_errors_total",
    "Total number of errors in pool processing",
    ["pool_id", "stage"],
)


class PoolSettings(BaseModel):
    interval: int = Field(default=60, ge=1, description="Интервал в секундах")
    buy_symbol: str = Field(
        default="SOL_USDC", description="Символ для BUY, если нет балансов"
    )
    spend_percent: float = Field(
        default=100.0, ge=0.0, le=100.0, description="% USDC для BUY order"
    )


async def process_pool(pool):
    try:
        cfg = PoolSettings(**pool.settings)
    except ValidationError as e:
        ERROR_COUNT.labels(pool_id=str(pool.id), stage="validate_settings").inc()
        print(f"[Pool {pool.id}] Invalid settings: {e}")
        return

    accounts = await list_pool_accounts(pool.id)
    for acc in accounts:
        client = BackpackExchangeClient(api_key=acc.api_key, api_secret=acc.api_secret)
        # 1. баланс
        try:
            balance_resp = await client.get_balance()
        except Exception as e:
            ERROR_COUNT.labels(pool_id=str(pool.id), stage="get_balance").inc()
            print(f"[Pool {pool.id}][Acc {acc.id}] Error fetching balance: {e}")
            continue
        # 2. lend/borrow позиции
        try:
            lend_resp = await client.get_borrow_lend_positions()
        except Exception as e:
            ERROR_COUNT.labels(pool_id=str(pool.id), stage="get_lend").inc()
            print(f"[Pool {pool.id}][Acc {acc.id}] Error fetching lend positions: {e}")
            lend_resp = SimpleNamespace(positions=[])
        # net-qty из lend
        net_qty = {}
        for pos in getattr(lend_resp, "positions", []):
            try:
                sym = (
                    pos.get("symbol")
                    if isinstance(pos, dict)
                    else getattr(pos, "symbol", None)
                )
                raw = (
                    pos.get("netExposureQuantity")
                    if isinstance(pos, dict)
                    else getattr(pos, "netExposureQuantity", None)
                )
                if sym and raw is not None:
                    net_qty[sym.replace("_USDC", "")] = Decimal(str(raw))
            except:
                continue
        # вычисляем USD-балансы
        balances_usd = []
        for token, data in getattr(balance_resp, "balances", {}).items():
            if token == "USDC":
                continue
            try:
                avail = Decimal(str(getattr(data, "available", 0)))
                total = avail + net_qty.get(token, Decimal(0))
                if total <= 0:
                    continue
                ob = await client.get_order_book_depth(f"{token}_USDC")
                asks = ob.get("asks", [])
                if not asks:
                    continue
                price = Decimal(str(asks[0][0]))
            except Exception as e:
                ERROR_COUNT.labels(
                    pool_id=str(pool.id), stage="calculate_balances"
                ).inc()
                continue
            balances_usd.append(
                {"token": token, "quantity": total, "usd": float(total * price)}
            )
        balances_usd.sort(key=lambda x: x["usd"], reverse=True)
        # Торговля
        if not balances_usd:
            action = "buy"
            usdc_data = getattr(balance_resp, "balances", {}).get("USDC")
            try:
                usdc_avail = Decimal(str(getattr(usdc_data, "available", 0)))
            except:
                usdc_avail = Decimal(0)
            spend_amount = usdc_avail * Decimal(cfg.spend_percent) / Decimal(100)
            if spend_amount <= 0:
                continue
            try:
                ob_buy = await client.get_order_book_depth(cfg.buy_symbol)
                asks_buy = ob_buy.get("asks", [])
                price_buy = Decimal(str(asks_buy[0][0])) if asks_buy else Decimal(0)
                qty = (spend_amount / price_buy).quantize(
                    Decimal("0.001"), rounding=ROUND_DOWN
                )
                res = await client.create_order(
                    symbol=cfg.buy_symbol,
                    side="Bid",
                    quantity=str(qty),
                    order_type="Market",
                )
                ORDER_COUNT.labels(pool_id=str(pool.id), action=action).inc()
                print(
                    f"[Pool {pool.id}][Acc {acc.id}] BUY {cfg.buy_symbol} qty={qty}: {res}"
                )
            except Exception as e:
                ERROR_COUNT.labels(pool_id=str(pool.id), stage="execute_buy").inc()
                print(f"[Pool {pool.id}][Acc {acc.id}] Error on BUY: {e}")
        else:
            action = "sell"
            top = balances_usd[0]
            symbol = top["token"] + "_USDC"
            try:
                qty = Decimal(top["quantity"]).quantize(
                    Decimal("0.001"), rounding=ROUND_DOWN
                )
                res = await client.create_order(
                    symbol=symbol, side="Ask", quantity=str(qty), order_type="Market"
                )
                ORDER_COUNT.labels(pool_id=str(pool.id), action=action).inc()
                print(f"[Pool {pool.id}][Acc {acc.id}] SELL {symbol} qty={qty}: {res}")
            except Exception as e:
                ERROR_COUNT.labels(pool_id=str(pool.id), stage="execute_sell").inc()
                print(f"[Pool {pool.id}][Acc {acc.id}] Error on SELL: {e}")


async def main():
    # Запустим HTTP сервер для Prometheus метрик на порту 8000
    start_http_server(8001)
    while True:
        with CYCLE_LATENCY.time():
            pools = await get_active_pools()
            await asyncio.gather(*(process_pool(p) for p in pools))
        # вычислить паузу
        intervals = []
        for p in pools:
            try:
                cfg = PoolSettings(**p.settings)
                intervals.append(cfg.interval)
            except:
                continue
        await asyncio.sleep(min(intervals) if intervals else 60)


if __name__ == "__main__":
    asyncio.run(main())
