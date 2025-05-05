# src/bot/features/proxy/handlers/add.py  (новый файл или переименовали)
from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
import os
import socket

from src.bot.features.proxy.keyboards import proxy_menu_keyboard
from src.bot.features.proxy.states import ProxyStates
from src.bot.triggers import Texts
from src.core.repositories import proxy as proxy_repo

router = Router()


# ─────────────────────────── helpers ────────────────────────────
def parse_proxy_file(path: str) -> list[str]:
    with open(path, encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def resolve_proxies(lines: list[str]) -> tuple[list[str], str, list[str]]:
    host_cache: dict[str, str] = {}
    resolved: list[str] = []
    first_old = first_new = None

    for raw in lines:
        parts = raw.split(":")
        host = parts[0]
        ip = host_cache.get(host)
        if ip is None:
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


def confirmation_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да", callback_data="proxy_confirm")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="proxy_cancel")],
        ]
    )


# ─────────────────────────── меню ───────────────────────────────
@router.message(F.text == Texts.Proxy.HOME.value)
async def proxy_menu(message: Message) -> None:
    await message.answer("Меню прокси", reply_markup=proxy_menu_keyboard())


# ─────────────────────────── шаг 0 ──────────────────────────────
@router.message(F.text == "Добавить прокси")
async def proxy_add_start(message: Message, state: FSMContext) -> None:
    await state.set_state(ProxyStates.adding)
    await message.answer("Пришлите файл .txt с прокси, затем укажите страну")


# ─────────────────────────── шаг 1: файл ───────────────────────
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


# ─────────────────────────── шаг 2: страна ─────────────────────
@router.message(StateFilter(ProxyStates.adding), F.text)
async def proxy_country(message: Message, state: FSMContext) -> None:
    country: str = message.text.strip()
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


# ─────────────────────────── шаг 3: подтверждение ───────────────
@router.callback_query(StateFilter(ProxyStates.adding), F.data == "proxy_confirm")
async def proxy_confirm(cb: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    objs = await proxy_repo.add_proxies(data["proxies"], data["country"])

    await cb.message.answer(
        f"Добавлено прокси: {len(objs)}", reply_markup=proxy_menu_keyboard()
    )
    await state.clear()


@router.callback_query(StateFilter(ProxyStates.adding), F.data == "proxy_cancel")
async def proxy_cancel(cb: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await cb.message.answer(
        "Добавление прокси отменено", reply_markup=proxy_menu_keyboard()
    )
