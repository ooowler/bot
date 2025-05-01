from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, func

from src.bot.callbacks import Callbacks
from src.bot.keyboards.start.start import get_welcome_keyboard
from src.core.clients.databases.postgres import pg
from src.core.models import Proxy

show_proxy_router = Router()


# ─────────────────── FSM ──────────────────
class ProxyView(StatesGroup):
    waiting_country = State()
    waiting_limit = State()


# ───────── старт (кнопка «Прокси») ────────
@show_proxy_router.callback_query(F.data == Callbacks.Proxy.INFO)
async def proxy_view_start(cb: CallbackQuery, state: FSMContext):
    await state.set_state(ProxyView.waiting_country)
    await cb.message.edit_text(
        "🌍 Код страны (<code>*</code> — все):", parse_mode="HTML"
    )
    await cb.answer()


# ───────── country → ask limit ────────────
@show_proxy_router.message(ProxyView.waiting_country)
async def proxy_view_country(msg: Message, state: FSMContext):
    await state.update_data(country=msg.text.strip().upper() or "*")
    await state.set_state(ProxyView.waiting_limit)
    await msg.answer("🔢 Сколько строк вывести? (целое число)")


# ───────── limit → show list ──────────────
@show_proxy_router.message(ProxyView.waiting_limit)
async def proxy_view_list(msg: Message, state: FSMContext):
    try:
        limit = max(1, int(msg.text.strip()))
    except ValueError:
        await msg.answer("Нужно целое число.")
        return

    data = await state.get_data()
    country = data["country"]
    await state.clear()

    async with pg.session_maker() as session:
        base = select(Proxy)
        if country != "*":
            base = base.where(Proxy.country.ilike(country))

        total_cnt = await session.scalar(
            select(func.count()).select_from(base.subquery())
        )
        free_cnt = await session.scalar(
            select(func.count()).select_from(
                base.where(Proxy.in_use.is_(False)).subquery()
            )
        )

        items = (await session.scalars(base.limit(limit))).all()

    if not items:
        await msg.answer("❌ Ничего не найдено.", reply_markup=get_welcome_keyboard())
        return

    hdr = (
        f"<b>Найдено:</b> {total_cnt}   •   "
        f"<b>Свободно:</b> {free_cnt}\n"
        f"Показываю первые {len(items)} строк:\n\n"
    )
    body = "\n".join(
        f"{i+1}. <code>{p.ip}:{p.port}</code> • {p.country or '??'} • "
        f"{'🟢 free' if not p.in_use else '🔒 busy'}"
        for i, p in enumerate(items)
    )
    await msg.answer(hdr + body, parse_mode="HTML", reply_markup=get_welcome_keyboard())
