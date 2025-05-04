from __future__ import annotations

import io, json, re, socket, ipaddress, asyncio
from typing import Sequence

from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    Document,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from src.bot.triggers import Callbacks
from src.bot.keyboards.start.start import get_welcome_keyboard
from src.core.clients.databases.postgres import pg
from src.core.models import Proxy

# ─────────────────────────  Router  ──────────────────────────
add_proxy_router = Router()


# ─────────────────────────  FSM  ─────────────────────────────
class AddProxy(StatesGroup):
    waiting_country = State()
    waiting_file = State()
    confirm_format = State()


# ────────────  helper: inline‑KB «Да / Нет» ─────────────
def confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Всё верно", callback_data="proxy_confirm_yes"
                ),
                InlineKeyboardButton(
                    text="❌ Отмена", callback_data="proxy_confirm_no"
                ),
            ]
        ]
    )


# ─────────────────────────  REGEX‑парсеры  ─────────────────────────
PATTERNS = {
    "ip_port_login_pass": re.compile(
        r"^(?P<host>[^:]+):(?P<port>\d{2,5}):(?P<login>[^:]+):(?P<password>.+)$"
    ),
    "login_pass_ip_port": re.compile(
        r"^(?P<login>[^:@]+):(?P<password>[^@]+)@(?P<host>[^:]+):(?P<port>\d{2,5})$"
    ),
}


async def _resolve(host: str) -> str | None:
    """DNS‑резолв (sync через executor)."""
    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(None, socket.gethostbyname, host)
    except socket.gaierror:
        return None


async def parse_line(raw: str) -> dict | None:
    """Парс одной строки → dict либо None."""
    raw = raw.strip()
    for name, pat in PATTERNS.items():
        m = pat.match(raw)
        if not m:
            continue

        d = m.groupdict()
        ip = d["host"]
        if not re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", ip):
            ip = await _resolve(ip) or ""
        try:
            ipaddress.IPv4Address(ip)
        except ipaddress.AddressValueError:
            return None

        return {
            "ip": ip,
            "port": int(d["port"]),
            "login": d["login"],
            "password": d["password"],
            "format": name,
        }
    return None


# ────────────────────  STEP 0 – старт  ─────────────────────
@add_proxy_router.callback_query(F.data == Callbacks.Proxy.ADD)
async def proxy_add_start(cb: CallbackQuery, state: FSMContext):
    await state.set_state(AddProxy.waiting_country)
    await cb.message.edit_text(
        "🌍 Введите страну (или <b>*</b> — «без страны»):",
        parse_mode="HTML",
    )
    await cb.answer()


# ────────────────────  STEP 1 – страна  ────────────────────
@add_proxy_router.message(AddProxy.waiting_country)
async def proxy_add_country(msg: Message, state: FSMContext):
    country = msg.text.strip().upper()

    await state.update_data(country=country if country != "*" else None)
    await state.set_state(AddProxy.waiting_file)
    await msg.answer(
        "📄 Пришлите TXT‑файл с прокси.\n\n"
        "Поддерживаются форматы:\n"
        "• <code>ip:port:login:password</code>\n"
        "• <code>login:password@ip:port</code>",
        parse_mode="HTML",
    )


# ────────────────────  STEP 2 – файл  ──────────────────────
@add_proxy_router.message(AddProxy.waiting_file, F.document)
async def proxy_add_file(msg: Message, state: FSMContext):
    doc: Document = msg.document
    if doc.mime_type not in {"text/plain", "application/octet-stream"}:
        await msg.answer("Нужен TXT‑файл.")
        return

    # скачиваем в память
    buf = io.BytesIO()
    await msg.bot.download(doc, destination=buf)
    buf.seek(0)
    text = buf.read().decode(errors="ignore")
    lines = [ln for ln in text.splitlines() if ln.strip()]

    # превью 1‑й валидной строки
    preview = None
    for ln in lines:
        preview = await parse_line(ln)
        if preview:
            break

    if not preview:
        await state.clear()
        await msg.answer(
            "❌ Не удалось распознать формат. Поддерживаются 2 вида:\n"
            "<code>ip:port:login:password</code>  или  <code>login:password@ip:port</code>",
            parse_mode="HTML",
            reply_markup=get_welcome_keyboard(),
        )
        return

    await state.update_data(
        raw_lines=json.dumps(lines),
        fmt=preview.pop("format"),
    )

    txt = (
        "Я разобрал первую строку так:\n"
        f"• IP: <code>{preview['ip']}</code>\n"
        f"• Port: <code>{preview['port']}</code>\n"
        f"• Login: <code>{preview['login']}</code>\n"
        f"• Password: <code>{preview['password']}</code>\n\n"
        "✅ Всё верно?"
    )
    await state.set_state(AddProxy.confirm_format)
    await msg.answer(txt, parse_mode="HTML", reply_markup=confirm_kb())


# ────────────────────  STEP 3 – подтверждение  ─────────────
@add_proxy_router.callback_query(
    AddProxy.confirm_format, F.data.in_({"proxy_confirm_yes", "proxy_confirm_no"})
)
async def proxy_confirm(cb: CallbackQuery, state: FSMContext):
    if cb.data == "proxy_confirm_no":
        await state.clear()
        await cb.message.edit_text(
            "Операция отменена.", reply_markup=get_welcome_keyboard()
        )
        await cb.answer()
        return

    data = await state.get_data()
    country = data["country"]
    fmt_name = data["fmt"]
    raw_lines: Sequence[str] = json.loads(data["raw_lines"])
    await state.clear()

    parsed_ok, bad = [], []
    for ln in raw_lines:
        p = await parse_line(ln)
        if not p or p["format"] != fmt_name:
            bad.append(ln)
            continue
        p.pop("format")
        p["country"] = country
        parsed_ok.append(p)

    # убираем дубликаты ip:port
    async with pg.session_maker() as session:
        existing = {
            (ip, prt) for ip, prt in await session.execute(select(Proxy.ip, Proxy.port))
        }
        new_objs = [
            Proxy(**p) for p in parsed_ok if (p["ip"], p["port"]) not in existing
        ]
        session.add_all(new_objs)
        await session.commit()

    await cb.message.edit_text(
        f"✅ Добавлено: <b>{len(new_objs)}</b>\n"
        f"⛔ Пропущено (ошибка/дубликат): <b>{len(raw_lines) - len(new_objs)}</b>",
        parse_mode="HTML",
        reply_markup=get_welcome_keyboard(),
    )
    await cb.answer()
