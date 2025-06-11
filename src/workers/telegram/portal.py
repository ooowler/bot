"""
Async monitor for price gaps in Portals Market NFT collections.

For every collection, we check the first two NFTs sorted by price (ascending).
If the price difference exceeds THRESHOLD_PERCENT (default 10 %), we send a Telegram
notification and remember that NFT so it is not alerted twice.

The script runs forever, repeating the scan every INTERVAL_SEC seconds.

Requirements:
    pip install aiohttp pydantic loguru

Environment variables:
    AUTH_PORTAL               – API token for portals‑market.com
    TELEGRAM_TOKEN            – Telegram Bot API token
    TELEGRAM_GIFTS_GROUP_ID   – Chat ID where alerts are sent (set "0" to disable)
"""

from __future__ import annotations

import asyncio
import os
from typing import Dict, List, Set

import aiohttp
from loguru import logger
from pydantic import BaseModel, Field

# -----------------------------------------------------
#  Configuration
# -----------------------------------------------------

BASE_URL = "https://portals-market.com/api"
HEADERS = {"Authorization": os.getenv("AUTH_PORTAL", "")}

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
CHAT_ID_ENV = os.getenv("TELEGRAM_GIFTS_GROUP_ID", "0")
CHAT_ID: int | None = int(CHAT_ID_ENV) if CHAT_ID_ENV != "0" else None

THRESHOLD_PERCENT = 10.0  # alert when 2nd cheapest NFT is >10 % above the floor
INTERVAL_SEC = 60         # repeat full scan every 60 s
MAX_CONCURRENCY = 10      # simultaneous NFT queries

if not HEADERS["Authorization"]:
    raise EnvironmentError("AUTH_PORTAL environment variable is not set")
if not BOT_TOKEN or CHAT_ID is None:
    logger.error(f"Invalid Telegram creds: BOT_TOKEN={bool(BOT_TOKEN)}, CHAT_ID={CHAT_ID}")
    raise EnvironmentError("TELEGRAM_TOKEN or TELEGRAM_GIFTS_GROUP_ID is not set or invalid")

# -----------------------------------------------------
#  Pydantic models mirroring the API schema
# -----------------------------------------------------

class Collection(BaseModel):
    id: str
    name: str
    short_name: str
    photo_url: str
    day_volume: str
    volume: str
    floor_price: str
    supply: int

class CollectionsResponse(BaseModel):
    collections: List[Collection]
    floor_changes: Dict = Field(default_factory=dict)

class Attribute(BaseModel):
    type: str
    value: str
    rarity_per_mille: float

class NFT(BaseModel):
    id: str
    tg_id: str
    collection_id: str
    external_collection_number: int
    owner_id: int
    name: str
    photo_url: str
    price: str
    attributes: List[Attribute]
    listed_at: str
    status: str
    animation_url: str
    emoji_id: str
    has_animation: bool
    floor_price: str
    unlocks_at: str | None

class NFTSearchResponse(BaseModel):
    results: List[NFT]

# -----------------------------------------------------
#  HTTP helpers
# -----------------------------------------------------

async def fetch_collections(
    session: aiohttp.ClientSession,
    *,
    limit: int = 100,
    sort_by: str = "floor_price+asc",
) -> CollectionsResponse:
    url = f"{BASE_URL}/collections?limit={limit}&sort_by={sort_by}"
    async with session.get(url, headers=HEADERS, timeout=30) as resp:
        resp.raise_for_status()
        return CollectionsResponse(**await resp.json())

async def fetch_nfts_for_collection(
    session: aiohttp.ClientSession,
    collection_id: str,
    *,
    offset: int = 0,
    limit: int = 20,
    sort_by: str = "price+asc",
) -> NFTSearchResponse:
    url = (
        f"{BASE_URL}/nfts/search?offset={offset}&limit={limit}"
        f"&sort_by={sort_by}&collection_id={collection_id}"
    )
    async with session.get(url, headers=HEADERS, timeout=30) as resp:
        resp.raise_for_status()
        return NFTSearchResponse(**await resp.json())

async def send_telegram_message(session: aiohttp.ClientSession, text: str):
    """Send a Telegram message using the given aiohttp session."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    params = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": "true",  # must be str, not bool
    }
    async with session.post(url, params=params, timeout=15) as resp:
        if resp.status != 200:
            data = await resp.text()
            logger.error(f"Telegram error {resp.status}: {data}")
        else:
            logger.debug("Telegram message sent")

# -----------------------------------------------------
#  Business logic
# -----------------------------------------------------

SEM = asyncio.Semaphore(MAX_CONCURRENCY)
NOTIFIED_NFTS: Set[str] = set()

async def process_collection(session: aiohttp.ClientSession, coll: Collection):
    """Check price gap for a collection and send Telegram alert if needed."""
    async with SEM:
        try:
            nfts_resp = await fetch_nfts_for_collection(session, coll.id)
        except Exception as exc:
            logger.error(f"{coll.short_name}: NFT fetch failed — {exc}")
            return

    results = nfts_resp.results
    if len(results) < 2:
        return

    p1, p2 = map(float, (results[0].price, results[1].price))
    if p1 == 0:
        return
    diff_pct = (p2 - p1) / p1 * 100

    if diff_pct > THRESHOLD_PERCENT and results[0].id not in NOTIFIED_NFTS:
        msg = (
            f"<b>{coll.name}</b> — price gap {diff_pct:.2f}%\n"
            f"1️⃣ {p1} TON\n2️⃣ {p2} TON\n"
            f"@portals"
        )
        await send_telegram_message(session, msg)
        NOTIFIED_NFTS.add(results[0].id)

async def run_cycle(session: aiohttp.ClientSession):
    try:
        coll_resp = await fetch_collections(session)
    except Exception as exc:
        logger.error(f"Failed to fetch collections: {exc}")
        return

    tasks = [process_collection(session, c) for c in coll_resp.collections]
    await asyncio.gather(*tasks)

async def scheduler():
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                await run_cycle(session)
            except Exception as e:
                logger.error(f"error run_cycle: {e}")
            finally:
                await asyncio.sleep(INTERVAL_SEC)

# -----------------------------------------------------
#  Entrypoint
# -----------------------------------------------------

if __name__ == "__main__":
    try:
        asyncio.run(scheduler())
    except KeyboardInterrupt:
        logger.info("Stopped by user")