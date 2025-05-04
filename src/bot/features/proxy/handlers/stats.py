from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy import select, func
from src.core.models import Proxy
from src.core.clients.databases.postgres import pg
from src.bot.triggers import Texts
from src.bot.features.proxy.keyboards import proxy_menu_keyboard

router = Router()


@router.message(F.text == Texts.Proxy.STATS)
async def proxy_stats(message: Message):
    async with pg.session_maker() as session:
        result = await session.execute(
            select(Proxy.country, func.count()).group_by(Proxy.country)
        )
        data = result.all()
    if not data:
        await message.answer("Прокси не найдены", reply_markup=proxy_menu_keyboard())
        return
    lines = [f"{country}: {count}" for country, count in data]
    await message.answer(
        "Статистика прокси по странам:\n" + "\n".join(lines),
        reply_markup=proxy_menu_keyboard(),
    )
