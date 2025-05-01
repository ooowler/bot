import random
from decimal import Decimal, ROUND_DOWN

from loguru import logger
from sqlalchemy import select

from src.core.clients.exchanges.backpack.utils import (
    _top_up_sol,
    _compute_total_usd_balance,
    _open_market_order,
    _select_random_main_account,
    _load_proxy_and_fake,
    _get_sub_accounts,
    LEVERAGE,
    SYMBOLS,
    MIN_DEPOSIT_USD,
)
from src.core.clients.databases.postgres import pg
from src.core.clients.exchanges.backpack.backpack import BackpackExchangeClient
from src.core.models import DepositAddress, Chain


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
