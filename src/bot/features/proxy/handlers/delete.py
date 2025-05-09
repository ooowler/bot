from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from src.bot.features.proxy.keyboards import proxy_menu_keyboard
from src.bot.features.proxy.states import ProxyStates
from src.bot.triggers import Texts
from src.core.repositories import proxy as proxy_repo

router = Router()


@router.message(F.text == Texts.Proxy.DELETE)
async def proxy_delete_start(message: Message, state: FSMContext) -> None:
    await state.set_state(ProxyStates.deleting_country)
    await message.answer(
        "Введите страну для удаления прокси",
        reply_markup=proxy_menu_keyboard(),
    )


@router.message(StateFilter(ProxyStates.deleting_country))
async def proxy_delete_country(message: Message, state: FSMContext) -> None:
    country: str = message.text.strip().upper()

    total: int = await proxy_repo.count_available_by_country(country)
    if total == 0:
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
async def proxy_delete_amount(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    country: str = data["country"]

    try:
        num: int = int(message.text.strip())
    except ValueError:
        await message.answer(
            "Введите корректное число", reply_markup=proxy_menu_keyboard()
        )
        return

    to_delete: int = min(num, data["total"])
    deleted: int = await proxy_repo.delete_available_by_country(country, to_delete)

    await message.answer(
        f"Удалено {deleted} прокси в {country}",
        reply_markup=proxy_menu_keyboard(),
    )
    await state.clear()
