import cloudscraper
import asyncio
import aiohttp
import json
from loguru import logger
import re
import os
import itertools
from prometheus_client import start_http_server, Gauge

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = int(os.getenv("TELEGRAM_GIFTS_GROUP_ID"))


GIFTS_FOUND = set()


def calc_top(l: list[float], value: float) -> float:
    l.sort()
    for i in range(len(l) - 1):
        if l[i] == value and l[i] != l[i + 1]:
            return round((i + 1) / len(l), 2)
        elif value < l[i]:
            return round((i) / len(l), 2)
        elif value < l[i + 1]:
            return round((i + 1) / len(l), 2)

    return 1.0


def parse_percentage(s: str) -> float | None:
    m = re.search(r"\(([\d.]+)%\)", s)
    return float(m.group(1)) if m else None


GIFTS = [
    "Restless Jar",
    "Heart Locket",
    "Bow Tie",
    "Heroic Helmet",
    "Nail Bracelet",
    "Light Sword",
    "Gem Signet",
    "Bonded Ring",
    "Holiday Drink",
    "Xmas Stocking",
    "Snake Box",
    "Pet Snake",
    "Big Year",
    "Astral Shard",
    "B-Day Candle",
    "Berry Box",
    "Bunny Muffin",
    "Candy Cane",
    "Cookie Heart",
    "Crystal Ball",
    "Desk Calendar",
    "Diamond Ring",
    "Durov's Cap",
    "Easter Egg",
    "Electric Skull",
    "Eternal Candle",
    "Eternal Rose",
    "Evil Eye",
    "Flying Broom",
    "Genie Lamp",
    "Ginger Cookie",
    "Hanging Star",
    "Hex Pot",
    "Homemade Cake",
    "Hypno Lollipop",
    "Ion Gem",
    "Jack-in-the-Box",
    "Jelly Bunny",
    "Jester Hat",
    "Jingle Bells",
    "Kissed Frog",
    "Lol Pop",
    "Loot Bag",
    "Love Candle",
    "Love Potion",
    "Lunar Snake",
    "Mad Pumpkin",
    "Magic Potion",
    "Mini Oscar",
    "Neko Helmet",
    "Party Sparkler",
    "Perfume Bottle",
    "Plush Pepe",
    "Precious Peach",
    "Record Player",
    "Sakura Flower",
    "Santa Hat",
    "Scared Cat",
    "Sharp Tongue",
    "Signet Ring",
    "Skull Flower",
    "Sleigh Bell",
    "Snow Globe",
    "Snow Mittens",
    "Spiced Wine",
    "Spy Agaric",
    "Star Notepad",
    "Swiss Watch",
    "Tama Gadget",
    "Top Hat",
    "Toy Bear",
    "Trapped Heart",
    "Vintage Cigar",
    "Voodoo Doll",
    "Winter Wreath",
    "Witch Hat",
]

API_URL = "https://gifts2.tonnel.network/api/pageGifts"


scraper = cloudscraper.create_scraper(
    browser={
        "platform": "linux",
        "browser": "chrome",
        "mobile": False,
    }
)
scraper.get("https://gifts2.tonnel.network/")
cookie_header = "; ".join(f"{c.name}={c.value}" for c in scraper.cookies)
HEADERS = {
    "Accept": "*/*",
    "Accept-Language": "ru,en;q=0.9",
    "Content-Type": "application/json",
    "Origin": "https://market.tonnel.network",
    "priority": "u=1, i",
    "Referer": "https://market.tonnel.network/",
    "sec-ch-ua": '"Not A(Brand";v="8", "Chromium";v="132", "YaBrowser";v="25.2", "Yowser";v="2.5"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Linux"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/132.0.0.0 YaBrowser/25.2.0.0 Safari/537.36"
    ),
    "Cookie": cookie_header,
}


async def send_telegram_message(text: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    params = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            if resp.status != 200:
                data = await resp.text()
                logger.error(f"Ошибка отправки в Telegram: {resp.status}, {data}")
            else:
                logger.debug("Сообщение успешно отправлено в Telegram.")


async def fetch_page_gifts(
    session: aiohttp.ClientSession,
    *,
    page: int = 1,
    limit: int = 30,
    gift_names: list[str] | None = None,
    asset: str = "TON",
    sort_fields: dict[str, int] | None = None,
    ref: int = 0,
    price_range: None | dict = None,
    user_auth: str = "",
) -> dict | str:
    if gift_names is None:
        gift_names = []
    if sort_fields is None:
        sort_fields = {"message_post_time": -1, "gift_id": -1}

    sort_str = json.dumps(sort_fields, separators=(",", ":"))
    filter_dict = {
        "price": {"$exists": True},
        "buyer": {"$exists": False},
        "asset": asset,
    }
    if gift_names:
        filter_dict["gift_name"] = {"$in": gift_names}
    if price_range is not None:
        filter_dict["price_range"] = price_range

    filter_str = json.dumps(filter_dict, separators=(",", ":"))

    payload = {
        "page": page,
        "limit": limit,
        "sort": sort_str,
        "filter": filter_str,
        "ref": ref,
        "price_range": price_range,
        "user_auth": user_auth,
    }

    def sync_post():
        return scraper.post(API_URL, headers=HEADERS, json=payload)

    response = await asyncio.to_thread(sync_post)

    content_type = response.headers.get("Content-Type", "")
    if content_type.startswith("application/json"):
        data = response.json()
    else:
        data = response.text[:200]

    return {"status": response.status_code, "body": data}


PRICE_GAUGE = Gauge("gifts_price", "Price of gift at specific rank", ["gift", "rank"])


async def main():
    start_http_server(8002)

    for gift in itertools.cycle(GIFTS):
        try:
            async with aiohttp.ClientSession() as session:
                result1 = await fetch_page_gifts(
                    session,
                    page=1,
                    limit=30,
                    gift_names=[gift],
                    asset="TON",
                    sort_fields={"price": 1, "gift_id": -1},
                    ref=0,
                    price_range=None,
                    user_auth="",
                )
                logger.info(f"parse gift: {gift}")
                body = result1["body"]
                if len(body) == 0:
                    continue

                if len(body) >= 1:
                    PRICE_GAUGE.labels(gift=gift, rank="1").set(body[0]["price"])
                if len(body) >= 3:
                    PRICE_GAUGE.labels(gift=gift, rank="3").set(body[2]["price"])
                if len(body) >= 5:
                    PRICE_GAUGE.labels(gift=gift, rank="5").set(body[4]["price"])
                if len(body) >= 10:
                    PRICE_GAUGE.labels(gift=gift, rank="10").set(body[9]["price"])

                model_perc, symbol_perc, backdrop_perc = [], [], []
                first = body[0]
                floor = first["price"]
                for item in body:
                    model_perc.append(parse_percentage(item["model"]))
                    symbol_perc.append(parse_percentage(item["symbol"]))
                    backdrop_perc.append(parse_percentage(item["backdrop"]))

                for i, item in enumerate(body, start=1):
                    gift_id = item["gift_id"]
                    model_top = calc_top(model_perc, parse_percentage(item["model"]))
                    symbol_top = calc_top(model_perc, parse_percentage(item["symbol"]))
                    backdrop_top = calc_top(
                        model_perc, parse_percentage(item["backdrop"])
                    )

                    if (
                        all(x <= 0.01 for x in (model_top, symbol_top, backdrop_top))
                        and item["price"] < floor * 1.1
                        and gift_id not in GIFTS_FOUND
                    ):
                        message = (
                            f"Редкий предмет"
                            f"Name: {item['name']} (gift_num: {item['gift_num']})\n"
                            f"price: {item['price']} (+{round(100 * (item['price'] / floor) - 100, 2)}%)\n"
                            f"Model {item['model']}%\n"
                            f"Symbol {item['symbol']}%\n"
                            f"Backdrop {item['backdrop']}%\n"
                            f"Buy: @Tonnel_Network_bot"
                        )
                        GIFTS_FOUND.add(gift_id)
                        await send_telegram_message(message)

                    elif (
                        i == 2
                        and floor * 1.15 < item["price"]
                        and first["gift_id"] not in GIFTS_FOUND
                    ):
                        message = (
                            f"Дешевый предмет (дешевле на {round(100 * (item['price'] / floor) - 100, 2)}%)\n"
                            f"Name: {first['name']} (gift_num: {first['gift_num']})\n"
                            f"price: {round(first['price'], 3)}\n"
                            f"Model {first['model']}\n"
                            f"Symbol {first['symbol']}\n"
                            f"Backdrop {first['backdrop']}\n"
                            f"Buy: @Tonnel_Network_bot"
                        )
                        GIFTS_FOUND.add(first["gift_id"])
                        await send_telegram_message(message)
        except Exception as e:
            logger.error(f"ERROR: {e}")


if __name__ == "__main__":
    asyncio.run(main())
