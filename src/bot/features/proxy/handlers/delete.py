from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, delete, func

from src.core.models import Proxy
from src.core.clients.databases.postgres import pg
from src.bot.triggers import Texts
from src.bot.features.proxy.keyboards import proxy_menu_keyboard
from src.bot.features.proxy.states import ProxyStates

router = Router()


@router.message(F.text == Texts.Proxy.DELETE)
async def proxy_delete_start(message: Message, state: FSMContext):
    await state.set_state(ProxyStates.deleting_country)
    await message.answer(
        "Введите страну для удаления прокси", reply_markup=proxy_menu_keyboard()
    )


@router.message(StateFilter(ProxyStates.deleting_country))
async def proxy_delete_country(message: Message, state: FSMContext):
    country = message.text.strip()
    async with pg.session_maker() as session:
        total = await session.scalar(
            select(func.count())
            .select_from(Proxy)
            .where(Proxy.country == country, Proxy.in_use == False)
        )
    if not total:
        await message.answer(
            f"Нет доступных прокси для удаления в стране {country}",
            reply_markup=proxy_menu_keyboard(),
        )
        await state.clear()
        return
    await state.update_data(country=country, total=total)
    await state.set_state(ProxyStates.deleting_amount)
    await message.answer(
        f"Найдено {total} прокси в {country}. Сколько удалить?",
        reply_markup=proxy_menu_keyboard(),
    )


@router.message(StateFilter(ProxyStates.deleting_amount))
async def proxy_delete_amount(message: Message, state: FSMContext):
    data = await state.get_data()
    country = data["country"]
    try:
        num = int(message.text.strip())
    except ValueError:
        await message.answer(
            "Введите корректное число", reply_markup=proxy_menu_keyboard()
        )
        return
    to_delete = min(num, data["total"])
    async with pg.session_maker() as session:
        ids = await session.scalars(
            select(Proxy.id)
            .where(Proxy.country == country, Proxy.in_use == False)
            .limit(to_delete)
        )
        await session.execute(delete(Proxy).where(Proxy.id.in_(ids.all())))
        await session.commit()
    await message.answer(
        f"Удалено {to_delete} прокси в {country}", reply_markup=proxy_menu_keyboard()
    )
    await state.clear()
