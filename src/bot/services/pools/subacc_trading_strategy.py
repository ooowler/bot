# src/bot/services/pools/subacc_trading_strategy.py

import random
from decimal import Decimal, ROUND_DOWN

from loguru import logger
from sqlalchemy import select

from src.core.clients.databases.postgres import pg
from src.core.clients.exchanges.backpack.backpack import BackpackExchangeClient
from src.core.models.base import Account, DepositAddress, Chain, Proxy, FakeHeader

# Constants
MIN_DEPOSIT_USD = Decimal("0.1")
LEVERAGE = 50
# SYMBOLS = ["ETH_USDC_PERP", "SOL_USDC_PERP", "BTC_USDC_PERP"]
SYMBOLS = ["ETH_USDC_PERP", "SOL_USDC_PERP"]


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
    headers = fake_obj.headers if fake_obj and fake_obj.headers else {}
    cookies = fake_obj.cookies if fake_obj and fake_obj.cookies else {}
    return proxy_url, headers, cookies


async def _compute_total_usd_balance(client: BackpackExchangeClient) -> Decimal:
    """
    Считаем общий USD-эквивалент баланса по всем активам на суб-акке.
    """
    balance = await client.get_balance()
    lend = await client.get_borrow_lend_positions()
    tickers = await client.get_all_tickers()
    prices = {t["symbol"]: Decimal(t["lastPrice"]) for t in tickers}

    net_qty = {
        p["symbol"].replace("_USDC", ""): Decimal(p.get("netQuantity", "0"))
        for p in lend
        if isinstance(p.get("netQuantity"), str)
    }

    total_usd = Decimal("0")
    for token, data in balance.items():
        available = Decimal(data.get("available", "0"))
        qty = available + net_qty.get(token, Decimal("0"))
        if qty <= 0:
            continue
        if token == "USDC":
            total_usd += qty
        else:
            pair = f"{token}_USDC"
            price = prices.get(pair) or prices.get(f"{pair}_PERP")
            if price:
                total_usd += qty * price

    logger.debug("Computed total USD balance = {}", total_usd)
    return total_usd


async def _top_up_sol(
    main_client: BackpackExchangeClient, sub_id: int, sol_address: str
) -> None:
    """
    Топ-ап суб-акка в SOL, если USD-эквивалента меньше MIN_DEPOSIT_USD.
    """
    book = await main_client.get_order_book_depth("SOL_USDC")
    asks = book.get("asks", [])
    if not asks:
        logger.error("Sub {}: cannot fetch SOL_USDC book", sub_id)
        return
    price = Decimal(asks[0][0])
    qty = (MIN_DEPOSIT_USD / price).quantize(Decimal("1e-6"), ROUND_DOWN) or Decimal(
        "1e-6"
    )
    logger.info("Sub {}: top-up {} SOL (~${})", sub_id, qty, MIN_DEPOSIT_USD)
    resp = await main_client.request_withdrawal(
        address=sol_address,
        blockchain="Solana",
        symbol="SOL",
        quantity=str(qty),
    )
    logger.info("Sub {}: withdrawal response: {}", sub_id, resp)


async def _open_market_order(
    client: BackpackExchangeClient,
    symbol: str,
    side: str,
    amount_usd: Decimal,
    pool_id: int,
    sub_id: int,
) -> dict:
    """
    Открывает маркет-фьючерс (symbol_PERP) по объему amount_usd.
    """
    depth = await client.get_order_book_depth(symbol)
    book = depth.get("bids" if side == "Bid" else "asks", [])
    if not book:
        logger.error("Pool {} Sub {}: no book for {}", pool_id, sub_id, symbol)
        return
    price = Decimal(book[-1][0] if side == "Bid" else book[0][0])
    precision = abs(Decimal(book[0][1]).as_tuple().exponent)
    step = Decimal(f"1e-{precision}")
    qty = (amount_usd / price).quantize(step, ROUND_DOWN) or step

    logger.info(
        "Pool {} Sub {}: placing {} {} qty={} (~${})",
        pool_id,
        sub_id,
        side,
        symbol,
        qty,
        amount_usd,
    )
    resp = await client.create_order(
        symbol=symbol,
        side=side,
        quantity=str(qty),
        order_type="Market",
    )
    logger.info(
        "Pool {} Sub {}: order response for {} -> {}", pool_id, sub_id, symbol, resp
    )

    return resp


async def run_subacc_trading_strategy(pool_id: int) -> None:
    logger.info("Pool {}: start strategy", pool_id)

    main = await _select_random_main_account()
    if not main:
        logger.warning("Pool {}: no main accounts", pool_id)
        return

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
        logger.warning("Pool {}: main {} has no subs", pool_id, main.id)
        return

    for sub in subs:
        logger.info("Pool {}: processing sub {} ({})", pool_id, sub.id, sub.wallet)
        proxy_url, headers, cookies = await _load_proxy_and_fake(sub.id)
        sub_client = BackpackExchangeClient(
            base_url="https://api.backpack.exchange/",
            api_key=sub.api_key,
            api_secret=sub.api_secret,
            proxy_url=proxy_url,
            fake_headers=headers,
            cookies=cookies,
        )

        # 1) Проверяем открытые perp-позиции
        positions = await sub_client.get_open_positions()
        open_perms = [p for p in positions]
        # open_perms = [p for p in positions if abs(Decimal(p.get("netQuantity", 0))) > 0]
        if len(open_perms) in (2, 3):
            logger.info(
                "Pool {} Sub {}: already 2 or 3 open positions, skip", pool_id, sub.id
            )
            continue
        if len(open_perms) == 1:
            resp = await sub_client.close_all_perp_positions()
            await sub_client.update_account_settings(leverage_limit=LEVERAGE)
            logger.info("Pool {} Sub {}: closed positions -> {}", pool_id, sub.id, resp)

        if len(open_perms) == 0:
            await sub_client.update_account_settings(leverage_limit=LEVERAGE)

        # 2) Compute total USD balance across all tokens
        total_usd = await _compute_total_usd_balance(sub_client)

        # 3) Top-up if below threshold
        if total_usd < MIN_DEPOSIT_USD:
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
                logger.error("Pool {} Sub {}: no SOL address", pool_id, sub.id)

        alloc = (total_usd / len(SYMBOLS)).quantize(Decimal("0.000001"), ROUND_DOWN)
        primary = random.choice(["Bid", "Ask"])
        opposite = "Ask" if primary == "Bid" else "Bid"
        odd = random.randrange(2)

        for idx, sym in enumerate(SYMBOLS):
            side = opposite if idx == odd else primary
            for step in ["0.9", "0.8", "0.7", "0.6", "0.5"]:
                res = await _open_market_order(
                    sub_client,
                    symbol=sym,
                    side=side,
                    amount_usd=alloc * LEVERAGE * Decimal(step),
                    pool_id=pool_id,
                    sub_id=sub.id,
                )
                if res.get("createdAt"):
                    break
