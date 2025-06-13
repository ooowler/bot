from __future__ import annotations
import random
import asyncio
import os
from typing import Dict, List, Set

import aiohttp
from loguru import logger
from pydantic import BaseModel, Field
from prometheus_client import start_http_server, Gauge
from tenacity import retry, stop_after_attempt, wait_fixed

# -----------------------------------------------------
#  Configuration
# -----------------------------------------------------

BASE_URL = "https://portals-market.com/api"
HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Encoding": "gzip",
    "Accept-Language": "en-US,en;q=0.9",
    "Authorization": os.getenv("AUTH_PORTAL", ""),
    "Connection": "keep-alive",
    "Cookie": "",
    "Host": "portals-market.com",
    "Referer": "https://portals-market.com/",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko)"
    ),
}

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
CHAT_ID_ENV = os.getenv("TELEGRAM_GIFTS_GROUP_ID", "0")
CHAT_ID: int | None = int(CHAT_ID_ENV) if CHAT_ID_ENV != "0" else None

THRESHOLD_PERCENT = 10.0
INTERVAL_SEC = 60
MAX_CONCURRENCY = 3

if not HEADERS["Authorization"]:
    raise EnvironmentError("AUTH_PORTAL environment variable is not set")
if not BOT_TOKEN or CHAT_ID is None:
    logger.error(
        f"Invalid Telegram creds: BOT_TOKEN={bool(BOT_TOKEN)}, CHAT_ID={CHAT_ID}"
    )
    raise EnvironmentError(
        "TELEGRAM_TOKEN or TELEGRAM_GIFTS_GROUP_ID is not set or invalid"
    )

# -----------------------------------------------------
#  Prometheus Metrics
# -----------------------------------------------------

NFT_PRICE_GAUGE = Gauge(
    "portals_nft_price",
    "Price of NFT at specific rank in a collection",
    ["collection", "rank"],
)
PRICE_GAP_GAUGE = Gauge(
    "portals_price_gap_percent",
    "Price gap percent between 2nd and 1st cheapest NFT",
    ["collection"],
)

# -----------------------------------------------------
#  Pydantic models
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


class NFT(BaseModel):
    id: str
    tg_id: str
    collection_id: str
    external_collection_number: int
    owner_id: int
    name: str
    photo_url: str
    price: str
    attributes: List[Dict]
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
    limit: int = 10,
    sort_by: str = "price+asc",
) -> NFTSearchResponse:
    url = f"{BASE_URL}/nfts/search?offset={offset}&limit={limit}&sort_by={sort_by}&collection_id={collection_id}"
    async with session.get(url, headers=HEADERS, timeout=30) as resp:
        await asyncio.sleep(random.uniform(0.5, 3))
        logger.info(f"fetch: {collection_id}")
        resp.raise_for_status()
        return NFTSearchResponse(**await resp.json())


@retry(stop=stop_after_attempt(3), wait=wait_fixed(2), reraise=True)
async def try_send_photo(session: aiohttp.ClientSession, text: str, photo_url: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    data = aiohttp.FormData()
    data.add_field("chat_id", str(CHAT_ID))
    data.add_field("caption", text)
    data.add_field("parse_mode", "HTML")
    data.add_field("photo", photo_url)
    async with session.post(url, data=data, timeout=15) as resp:
        if resp.status != 200:
            raise RuntimeError(f"photo failed: {await resp.text()}")


async def send_telegram_message(
    session: aiohttp.ClientSession, text: str, photo_url: str | None = None
):
    if photo_url:
        try:
            await try_send_photo(session, text, photo_url)
            logger.debug("Telegram photo sent")
            return
        except Exception as e:
            logger.warning(f"Fallback to text, photo failed: {e}")
            text += f'\n📷 <a href="{photo_url}">[open image]</a>'

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    params = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": "true",
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
    async with SEM:
        try:
            resp = await fetch_nfts_for_collection(session, coll.id)
        except Exception as exc:
            logger.error(f"{coll.short_name}: NFT fetch failed — {exc}")
            return

    results = resp.results
    if len(results) < 2:
        return

    p1 = float(results[0].price)
    p2 = float(results[1].price)
    if p1 == 0:
        return
    diff_pct = (p2 - p1) / p1 * 100

    for rank in (1, 3, 5, 10):
        if len(results) >= rank:
            nft = results[rank - 1]
            price = float(nft.price)
            NFT_PRICE_GAUGE.labels(collection=coll.short_name, rank=str(rank)).set(
                price
            )

    PRICE_GAP_GAUGE.labels(collection=coll.short_name).set(diff_pct)

    if diff_pct > THRESHOLD_PERCENT and results[0].id not in NOTIFIED_NFTS:
        nft = results[0]
        nft_link = f"https://t.me/portals/market?startapp=gift_{nft.id}"
        msg = (
            f"<b>{coll.name}</b> — price gap {diff_pct:.2f}%\n"
            f"1️⃣ {p1} TON\n2️⃣ {p2} TON\n"
            f'<a href="{nft_link}">Gift Link</a>'
        )
        await send_telegram_message(session, msg, nft.photo_url)
        exit(0)
        NOTIFIED_NFTS.add(nft.id)


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


if __name__ == "__main__":
    start_http_server(8000)
    try:
        asyncio.run(scheduler())
    except KeyboardInterrupt:
        logger.info("Stopped by user")
