import os
import re
import json
import asyncio
import cloudscraper
import httpx
from loguru import logger
from prometheus_client import start_http_server, Gauge
import random
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = int(os.getenv("TELEGRAM_GIFTS_GROUP_ID"))

GIFTS = [
    "Restless Jar","Heart Locket","Bow Tie","Heroic Helmet","Nail Bracelet",
    "Light Sword","Gem Signet","Bonded Ring","Holiday Drink","Xmas Stocking",
    "Snake Box","Pet Snake","Big Year","Astral Shard","B-Day Candle",
    "Berry Box","Bunny Muffin","Candy Cane","Cookie Heart","Crystal Ball",
    "Desk Calendar","Diamond Ring","Durov's Cap","Easter Egg","Electric Skull",
    "Eternal Candle","Eternal Rose","Evil Eye","Flying Broom","Genie Lamp",
    "Ginger Cookie","Hanging Star","Hex Pot","Homemade Cake","Hypno Lollipop",
    "Ion Gem","Jack-in-the-Box","Jelly Bunny","Jester Hat","Jingle Bells",
    "Kissed Frog","Lol Pop","Loot Bag","Love Candle","Love Potion",
    "Lunar Snake","Mad Pumpkin","Magic Potion","Mini Oscar","Neko Helmet",
    "Party Sparkler","Perfume Bottle","Plush Pepe","Precious Peach",
    "Record Player","Sakura Flower","Santa Hat","Scared Cat","Sharp Tongue",
    "Signet Ring","Skull Flower","Sleigh Bell","Snow Globe","Snow Mittens",
    "Spiced Wine","Spy Agaric","Star Notepad","Swiss Watch","Tama Gadget",
    "Top Hat","Toy Bear","Trapped Heart","Vintage Cigar","Voodoo Doll",
    "Winter Wreath","Witch Hat"
]

GIFTS_FOUND = set()
GIFTS_LOCK = asyncio.Lock()
PRICE_GAUGE = Gauge("gifts_price","Price of gift at specific rank",["gift","rank"])
API_URL = "https://gifts2.tonnel.network/api/pageGifts"

def parse_percentage(s):
    m = re.search(r"\(([\d.]+)%\)",s)
    return float(m.group(1)) if m else None

def calc_top(l,value):
    l = sorted(l)
    for i in range(len(l)-1):
        if l[i] == value and l[i] != l[i+1]:
            return round((i+1)/len(l),2)
        if value < l[i]:
            return round(i/len(l),2)
        if value < l[i+1]:
            return round((i+1)/len(l),2)
    return 1.0

async def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    params = {"chat_id":CHAT_ID,"text":text,"parse_mode":"HTML"}
    async with httpx.AsyncClient() as client:
        resp = await client.get(url,params=params)
        if resp.status_code != 200:
            logger.error(f"Ошибка отправки в Telegram: {resp.status_code}, {resp.text}")

async def fetch_page_gifts_async(client,gift):
    payload = {
        "page":1,
        "limit":30,
        "sort":json.dumps({"price":1,"gift_id":-1},separators=(",",":")),
        "filter":json.dumps({"price":{"$exists":True},"buyer":{"$exists":False},"asset":"TON","gift_name":{"$in":[gift]}},separators=(",",":")),
        "ref":0,
        "price_range":None,
        "user_auth":""
    }
    resp = await client.post(API_URL,json=payload)
    if "application/json" in resp.headers.get("Content-Type",""):
        return resp.json()
    return []

logger.info(f"start")
async def gift_worker(gift,cookie_header):
    headers = {
        "Accept":"*/*",
        "Accept-Language":"ru,en;q=0.9",
        "Content-Type":"application/json",
        "Origin":"https://market.tonnel.network",
        "Referer":"https://market.tonnel.network/",
        "Cookie":cookie_header
    }
    async with httpx.AsyncClient(headers=headers) as client:
        while True:
            try:
                body = await fetch_page_gifts_async(client,gift)
                if body:
                    for rank,idx in zip(["1","3","5","10"],[0,2,4,9]):
                        if len(body) > idx:
                            PRICE_GAUGE.labels(gift=gift,rank=rank).set(body[idx]["price"])
                    floor = body[0]["price"]
                    model_perc = [parse_percentage(x["model"]) for x in body]
                    symbol_perc = [parse_percentage(x["symbol"]) for x in body]
                    backdrop_perc = [parse_percentage(x["backdrop"]) for x in body]
                    for i,item in enumerate(body,start=1):
                        gift_id = item["gift_id"]
                        model_top = calc_top(model_perc,parse_percentage(item["model"]))
                        symbol_top = calc_top(symbol_perc,parse_percentage(item["symbol"]))
                        backdrop_top = calc_top(backdrop_perc,parse_percentage(item["backdrop"]))
                        async with GIFTS_LOCK:
                            already = gift_id in GIFTS_FOUND
                        if not already and all(x<=0.01 for x in (model_top,symbol_top,backdrop_top)) and item["price"] < floor*1.1:
                            msg = f"Редкий предмет\nName: {item['name']} (gift_num: {item['gift_num']})\nprice: {item['price']} (+{round(100*(item['price']/floor)-100,2)}%)\nModel {item['model']}\nSymbol {item['symbol']}\nBackdrop {item['backdrop']}\nBuy: @Tonnel_Network_bot"
                            async with GIFTS_LOCK:
                                GIFTS_FOUND.add(gift_id)
                            await send_telegram_message(msg)
                        elif i == 2 and not already and floor*1.15 < item["price"]:
                            first = body[0]
                            msg = f"Дешёвый предмет\nName: {first['name']} (gift_num: {first['gift_num']})\nprice: {round(first['price'],3)}\nModel {first['model']}\nSymbol {first['symbol']}\nBackdrop {first['backdrop']}\nBuy: @Tonnel_Network_bot"
                            async with GIFTS_LOCK:
                                GIFTS_FOUND.add(first["gift_id"])
                            await send_telegram_message(msg)
            except Exception as e:
                logger.error(e)
            finally:
                await asyncio.sleep(random.uniform(0.2, 1.5))

async def main():
    scr = cloudscraper.create_scraper(browser={"platform":"linux","browser":"chrome","mobile":False})
    scr.get("https://gifts2.tonnel.network/")
    cookie_header = "; ".join(f"{c.name}={c.value}" for c in scr.cookies)
    start_http_server(8002)
    tasks = [asyncio.create_task(gift_worker(g,cookie_header)) for g in GIFTS]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
