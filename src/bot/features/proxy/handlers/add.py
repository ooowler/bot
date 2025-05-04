from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
import os
import socket

from src.bot.triggers import Texts
from src.bot.features.proxy.keyboards import proxy_menu_keyboard
from src.bot.features.proxy.states import ProxyStates
from src.core.clients.databases.postgres import pg
from src.core.models import Proxy

router = Router()


def parse_proxy_file(path: str) -> list[str]:
    with open(path, encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def resolve_proxies(lines: list[str]) -> tuple[list[str], str, str]:
    host_cache = {}
    resolved = []
    first_old = first_new = None
    for raw in lines:
        parts = raw.split(":")
        host = parts[0]
        if host in host_cache:
            ip = host_cache[host]
        else:
            try:
                ip = socket.gethostbyname(host)
            except socket.gaierror:
                ip = host
            host_cache[host] = ip
        if first_old is None:
            first_old, first_new = host, ip
        parts[0] = ip
        resolved.append(":".join(parts))
    mapping = f"{first_old} -> {first_new}" if first_old != first_new else first_old
    return resolved, mapping, resolved[0].split(":")


def get_confirmation_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да", callback_data="proxy_confirm")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="proxy_cancel")],
        ]
    )


def save_proxies_to_db(proxies: list[str], country: str) -> list[Proxy]:
    objs = []
    for raw in proxies:
        parts = raw.split(":")
        if len(parts) != 4:
            continue
        host, port, login, password = parts
        objs.append(
            Proxy(
                ip=host, port=int(port), login=login, password=password, country=country
            )
        )

    async def _save(session):
        session.add_all(objs)
        await session.commit()

    return objs, _save


@router.message(F.text == Texts.Proxy.HOME.value)
async def proxy_menu(message: Message):
    await message.answer("Меню прокси", reply_markup=proxy_menu_keyboard())


@router.message(F.text == "Добавить прокси")
async def proxy_add_start(message: Message, state: FSMContext):
    await state.set_state(ProxyStates.adding)
    await message.answer("Пришлите файл .txt с прокси, затем укажите страну")


@router.message(StateFilter(ProxyStates.adding), F.document)
async def proxy_file(message: Message, state: FSMContext):
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
    first = lines[0].split(":")
    if len(first) != 4:
        await message.answer(
            "Неверный формат первой строки", reply_markup=proxy_menu_keyboard()
        )
        await state.clear()
        return
    await state.update_data(proxies=lines)
    await message.answer("Теперь укажите страну для этих прокси")


@router.message(StateFilter(ProxyStates.adding), F.text)
async def proxy_country(message: Message, state: FSMContext):
    country = message.text.strip()
    data = await state.get_data()
    resolved, mapping, first_parts = resolve_proxies(data["proxies"])
    await state.update_data(proxies=resolved, country=country)
    ip, port, login, password = first_parts
    await message.answer(
        f"Проверьте первую строку прокси:\nHost: {mapping}\nPort: {port}\nLogin: {login}\nPassword: {password}\nCountry: {country}\nВсего записей: {len(resolved)}",
        reply_markup=get_confirmation_markup(),
    )


@router.callback_query(StateFilter(ProxyStates.adding), F.data == "proxy_confirm")
async def proxy_confirm(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    objs, saver = save_proxies_to_db(data["proxies"], data["country"])
    async with pg.session_maker() as session:
        await saver(session)
    await cb.message.answer(
        f"Добавлено прокси: {len(objs)}", reply_markup=proxy_menu_keyboard()
    )
    await state.clear()


@router.callback_query(StateFilter(ProxyStates.adding), F.data == "proxy_cancel")
async def proxy_cancel(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.answer(
        "Добавление прокси отменено", reply_markup=proxy_menu_keyboard()
    )
