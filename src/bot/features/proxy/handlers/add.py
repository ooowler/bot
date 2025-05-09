from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    Message,
)
import os

from src.bot.features.proxy.utils import parse_proxy_file, resolve_proxies
from src.bot.features.proxy.keyboards import confirmation_kb, proxy_menu_keyboard
from src.bot.features.proxy.states import ProxyStates
from src.bot.triggers import Callbacks, Texts
from src.core.repositories import proxy as proxy_repo

router = Router()


@router.message(F.text == Texts.Proxy.HOME)
async def proxy_menu(message: Message) -> None:
    await message.answer("Меню прокси", reply_markup=proxy_menu_keyboard())


@router.message(F.text == Texts.Proxy.ADD)
async def proxy_add_start(message: Message, state: FSMContext) -> None:
    await state.set_state(ProxyStates.adding)
    await message.answer("Пришлите файл .txt с прокси, затем укажите страну")


@router.message(StateFilter(ProxyStates.adding), F.document)
async def proxy_file(message: Message, state: FSMContext) -> None:
    path = f"/tmp/{message.document.file_unique_id}.txt"
    await message.bot.download(message.document, destination=path)

    try:
        lines = parse_proxy_file(path)
    finally:
        os.remove(path)

    if not lines:
        await message.answer(
            "Файл пуст или неверный формат", reply_markup=proxy_menu_keyboard()
        )
        await state.clear()
        return

    if len(lines[0].split(":")) != 4:
        await message.answer(
            "Неверный формат первой строки", reply_markup=proxy_menu_keyboard()
        )
        await state.clear()
        return

    await state.update_data(proxies=lines)
    await message.answer("Теперь укажите страну для этих прокси")


@router.message(StateFilter(ProxyStates.adding), F.text)
async def proxy_country(message: Message, state: FSMContext) -> None:
    country: str = message.text.strip().upper()
    data = await state.get_data()

    resolved, mapping, first_parts = resolve_proxies(data["proxies"])
    await state.update_data(proxies=resolved, country=country)

    ip, port, login, password = first_parts
    await message.answer(
        f"Проверьте первую строку прокси:\n"
        f"Host: {mapping}\nPort: {port}\nLogin: {login}\nPassword: {password}\n"
        f"Country: {country}\nВсего записей: {len(resolved)}",
        reply_markup=confirmation_kb(),
    )


@router.callback_query(
    StateFilter(ProxyStates.adding), F.data == Callbacks.Proxy.CONFIRM
)
async def proxy_confirm(cb: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    objs = await proxy_repo.add_proxies(data["proxies"], data["country"])

    await cb.message.answer(
        f"Добавлено прокси: {len(objs)}", reply_markup=proxy_menu_keyboard()
    )
    await state.clear()


@router.callback_query(
    StateFilter(ProxyStates.adding), F.data == Callbacks.Proxy.CANCEL
)
async def proxy_cancel(cb: CallbackQuery, state: FSMContext) -> None:
    await cb.message.answer(
        "Добавление прокси отменено", reply_markup=proxy_menu_keyboard()
    )
    await state.clear()
