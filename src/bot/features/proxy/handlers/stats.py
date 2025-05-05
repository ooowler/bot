from aiogram import F, Router
from aiogram.types import Message

from src.bot.triggers import Texts
from src.bot.features.proxy.keyboards import proxy_menu_keyboard
from src.core.repositories.proxy import country_stats

router = Router()


@router.message(F.text == Texts.Proxy.STATS)
async def proxy_stats(message: Message):
    data = await country_stats()

    if not data:
        await message.answer("Прокси не найдены", reply_markup=proxy_menu_keyboard())
        return

    lines = [f"{country or '–'}: {count}" for country, count in data]
    await message.answer(
        "Статистика прокси по странам:\n" + "\n".join(lines),
        reply_markup=proxy_menu_keyboard(),
    )
