import random
import json
from decimal import Decimal, ROUND_DOWN

from loguru import logger
from sqlalchemy import select

from src.core.clients.databases.postgres import pg
from src.core.clients.exchanges.backpack.backpack import BackpackExchangeClient
from src.core.models.base import Account, DepositAddress, Chain, Proxy, FakeHeader

# Constants
USD_TOP_UP = Decimal("0.1")
MIN_SOL_STEP = Decimal("0.000001")
MIN_BTC_STEP = Decimal("0.000001")


async def _select_random_main_account() -> Account | None:
    async with pg.session_maker() as session:
        mains = (
            await session.scalars(select(Account).where(Account.parent_id.is_(None)))
        ).all()
    return random.choice(mains) if mains else None


async def _get_sub_accounts(main_id: int) -> list[Account]:
    async with pg.session_maker() as session:
        subs = (
            await session.scalars(select(Account).where(Account.parent_id == main_id))
        ).all()
    return subs


async def _load_proxy_and_fake(account_id: int) -> tuple[str | None, dict, dict]:
    """
    Возвращает proxy_url, fake_headers и cookies для данного account_id.
    """
    async with pg.session_maker() as session:
        proxy_obj = await session.scalar(
            select(Proxy).where(Proxy.account_id == account_id, Proxy.in_use.is_(True))
        )
        fake_obj = await session.scalar(
            select(FakeHeader).where(FakeHeader.account_id == account_id)
        )
    proxy_url = None
    if proxy_obj:
        proxy_url = f"socks5://{proxy_obj.login}:{proxy_obj.password}@{proxy_obj.ip}:{proxy_obj.port}"
        logger.info("Constructed proxy_url: {}", proxy_url)
    fake_headers = fake_obj.headers if fake_obj and fake_obj.headers else {}
    cookies = fake_obj.cookies if fake_obj and fake_obj.cookies else {}
    return proxy_url, fake_headers, cookies


async def _sell_all_non_usdc(client: BackpackExchangeClient) -> None:
    balance = await client.get_balance()
    lend = await client.get_borrow_lend_positions()
    net_qty = {
        p["symbol"].replace("_USDC", ""): Decimal(p.get("netQuantity", "0"))
        for p in lend
        if isinstance(p.get("netQuantity"), str)
    }
    for token, data in balance.items():
        if token == "USDC":
            continue
        total = Decimal(data.get("available", "0")) + net_qty.get(token, Decimal(0))
        if total <= 0:
            continue
        pair = f"{token}_USDC"
        depth = await client.get_order_book_depth(pair)
        asks = depth.get("asks", [])
        if not asks:
            continue
        precision = abs(Decimal(asks[0][1]).as_tuple().exponent)
        qty = total.quantize(
            Decimal(f"1e-{precision}"), rounding=ROUND_DOWN
        ) or Decimal(f"1e-{precision}")
        await client.create_order(
            symbol=pair, side="Ask", quantity=str(qty), order_type="Market"
        )
        logger.info("Sold {} {} -> USDC", qty, token)


async def _compute_total_usdc(client: BackpackExchangeClient) -> Decimal:
    balance = await client.get_balance()
    lend = await client.get_borrow_lend_positions()
    avail = Decimal(balance.get("USDC", {}).get("available", 0))
    net = Decimal("0")
    for p in lend:
        if p.get("symbol") == "USDC":
            try:
                net = Decimal(p.get("netQuantity", "0"))
            except:
                pass
    total = avail + net
    logger.debug("Computed total USDC = {}", total)
    return total


async def _top_up_sol(
    main_client: BackpackExchangeClient, sub_id: int, sol_address: str
) -> None:
    depth = await main_client.get_order_book_depth("SOL_USDC")
    asks = depth.get("asks", [])
    if not asks:
        logger.error("Не удалось получить стакан SOL_USDC для топ-апа sub {}", sub_id)
        return
    ask_price = Decimal(asks[0][0])
    raw_qty = USD_TOP_UP / ask_price
    sol_qty = raw_qty.quantize(MIN_SOL_STEP, rounding=ROUND_DOWN) or MIN_SOL_STEP
    logger.info("Топ-ап: перевожу {} SOL на sub {}", sol_qty, sub_id)
    resp = await main_client.request_withdrawal(
        address=sol_address,
        blockchain="Solana",
        symbol="SOL",
        quantity=str(sol_qty),
    )
    logger.info("Withdrawal response for sub {}: {}", sub_id, resp)


async def _open_market_order(
    client: BackpackExchangeClient,
    symbol: str,
    side: str,
    amount_usd: Decimal,
    pool_id: int,
    sub_id: int,
) -> None:
    depth = await client.get_order_book_depth(symbol)
    bids = depth.get("bids", [])
    if not bids:
        logger.error("Pool {}: нет bids для {} sub {}", pool_id, symbol, sub_id)
        return
    price = Decimal(bids[-1][0])
    sample = bids[-1][1]
    precision = abs(Decimal(sample).as_tuple().exponent)
    step = Decimal(f"1e-{precision}")
    raw_qty = amount_usd / price
    qty = raw_qty.quantize(step, rounding=ROUND_DOWN) or step
    logger.info(
        "Pool {}: ордер {} {} qty={} на sub {}", pool_id, side, symbol, qty, sub_id
    )
    resp = await client.create_order(
        symbol=symbol, side=side, quantity=str(qty), order_type="Market"
    )
    logger.info(
        "Pool {}: ответ ордера {} для sub {} -> {}", pool_id, symbol, sub_id, resp
    )


async def run_subacc_trading_strategy(pool_id: int) -> None:
    """
    Основная стратегия: для каждого sub аккаунта в пуле продаются все токены,
    проверяется USDC, пополняется SOL и открываются perp ордера.
    """
    logger.info("Pool {}: запускаю стратегию", pool_id)

    main = await _select_random_main_account()
    if not main:
        logger.warning("Pool {}: нет main аккаунтов", pool_id)
        return

    logger.info("Pool {}: выбран main {} ({})", pool_id, main.id, main.wallet)
    proxy_url, headers, cookies = await _load_proxy_and_fake(main.id)
    main_client = BackpackExchangeClient(
        base_url="https://api.backpack.exchange/",
        api_key=main.api_key,
        api_secret=main.api_secret,
        proxy_url=proxy_url,
        fake_headers=headers,
        cookies=cookies,
    )

    subs = await _get_sub_accounts(main.id)
    if not subs:
        logger.warning("Pool {}: main {} не имеет sub", pool_id, main.id)
        return

    for sub in subs:
        logger.info("Pool {}: обрабатываю sub {} ({})", pool_id, sub.id, sub.wallet)
        proxy_url, headers, cookies = await _load_proxy_and_fake(sub.id)
        sub_client = BackpackExchangeClient(
            base_url="https://api.backpack.exchange/",
            api_key=sub.api_key,
            api_secret=sub.api_secret,
            proxy_url=proxy_url,
            fake_headers=headers,
            cookies=cookies,
        )

        # 0) Проверяем открытые perp позиции
        positions = await sub_client.get_open_positions()
        open_perps = [p for p in positions if abs(Decimal(p.get("netQuantity", 0))) > 0]
        if len(open_perps) == 2:
            logger.info(
                "Pool {}: sub {} уже имеет 2 позиции, пропускаю", pool_id, sub.id
            )
            continue
        if len(open_perps) == 1:
            resp = await sub_client.close_all_perp_positions()
            logger.info(
                "Pool {}: sub {} закрыты все позиции -> {}", pool_id, sub.id, resp
            )
            continue

        # 1) Sell non-USDC
        await _sell_all_non_usdc(sub_client)

        # 2) Compute total USDC
        total_usdc = await _compute_total_usdc(sub_client)
        if total_usdc < USD_TOP_UP:
            # Top-up SOL
            async with pg.session_maker() as session:
                sol_addr = await session.scalar(
                    select(DepositAddress.address).where(
                        DepositAddress.account_id == sub.id,
                        DepositAddress.chain == Chain.SOLANA,
                    )
                )
            if sol_addr:
                await _top_up_sol(main_client, sub.id, sol_addr)
            else:
                logger.error("Pool {}: у sub {} нет SOL адреса", pool_id, sub.id)
            continue

        # 3) Open perp market orders
        await _open_market_order(
            sub_client,
            symbol="SOL_USDC_PERP",
            side="Bid",
            amount_usd=USD_TOP_UP,
            pool_id=pool_id,
            sub_id=sub.id,
        )
        await _open_market_order(
            sub_client,
            symbol="BTC_USDC_PERP",
            side="Ask",
            amount_usd=USD_TOP_UP,
            pool_id=pool_id,
            sub_id=sub.id,
        )
