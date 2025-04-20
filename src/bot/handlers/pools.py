# src/bot/handlers/pools.py
from __future__ import annotations

from aiogram import Router, F
from aiogram.types import (
    CallbackQuery,
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from sqlalchemy import select, delete, func

from src.bot.keyboards.start.start import get_welcome_keyboard
from src.bot.callbacks import Callbacks
from src.core.clients.databases.postgres import pg
from src.core.models.pool import Pool, PoolType, PoolAccountLink, PoolStatus
from src.core.models.base import Account, User, UserAccountLink

pools_router = Router()


# ──────────────── клавиатуры ────────────────


def pools_panel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📋 Показать мои пулы", callback_data=Callbacks.Pools.SHOW
                )
            ],
            [
                InlineKeyboardButton(
                    text="➕ Новый пул", callback_data=Callbacks.Pools.ADD
                )
            ],
        ]
    )


def confirm_pool_kb(pid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🚀 Запустить", callback_data=f"pool_run:{pid}"
                ),
                InlineKeyboardButton(
                    text="♻️ Обновить", callback_data=f"pool_update:{pid}"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🛑 Остановить", callback_data=f"pool_stop:{pid}"
                ),
                InlineKeyboardButton(
                    text="❌ Удалить", callback_data=f"pool_del:{pid}"
                ),
            ],
            [InlineKeyboardButton(text="↩️ Назад", callback_data=Callbacks.Pools.INFO)],
        ]
    )


# ──────────────── FSM ────────────────


class NewPool(StatesGroup):
    label = State()


# ──────────────── обработчики ────────────────


@pools_router.callback_query(F.data == Callbacks.Pools.INFO)
async def pools_panel(cb: CallbackQuery):
    """Показать панель управления пулами."""
    await cb.answer()
    await cb.message.answer("🗂 Панель пулов:", reply_markup=pools_panel_kb())


@pools_router.callback_query(F.data == Callbacks.Pools.SHOW)
async def list_pools(cb: CallbackQuery):
    """Показать список существующих пулов."""
    await cb.answer()
    async with pg.session_maker() as sess:
        owner = await sess.scalar(
            select(User).where(User.telegram_id == str(cb.from_user.id))
        )
        if not owner:
            await cb.message.answer(
                "Сначала нажмите /start", reply_markup=get_welcome_keyboard()
            )
            return

        pools = (
            await sess.scalars(select(Pool).where(Pool.owner_id == owner.id))
        ).all()

    if not pools:
        await cb.message.answer(
            "❕ У вас пока нет пулов.", reply_markup=pools_panel_kb()
        )
        return

    text = "<b>Ваши пулы:</b>\n" + "\n".join(
        f"{p.id}. {p.label} — {'🚀' if p.is_active else '⏸️'}" for p in pools
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=p.label, callback_data=f"pool_manage:{p.id}")]
            for p in pools
        ]
        + [[InlineKeyboardButton(text="↩️ Назад", callback_data=Callbacks.Pools.INFO)]]
    )

    await cb.message.answer(text, parse_mode="HTML", reply_markup=kb)


@pools_router.callback_query(F.data == Callbacks.Pools.ADD)
async def ask_label(cb: CallbackQuery, state: FSMContext):
    """Начало создания пула — спрашиваем label."""
    await cb.answer()
    await state.set_state(NewPool.label)
    await cb.message.answer("📝 Введите название (label) нового пула:")


@pools_router.message(NewPool.label)
async def create_pool(msg: Message, state: FSMContext):
    """Создаём пул и наполняем его main‑акками, у которых есть sub‑акки."""
    label = msg.text.strip()
    await state.clear()

    async with pg.session_maker() as sess:
        owner = await sess.scalar(
            select(User).where(User.telegram_id == str(msg.from_user.id))
        )
        if not owner:
            await msg.answer(
                "Сначала нажмите /start", reply_markup=get_welcome_keyboard()
            )
            return

        # собираем parent_id для тех, у кого есть саб-акки
        rows = (
            await sess.execute(
                select(Account.parent_id, func.count())
                .where(Account.parent_id.isnot(None))
                .group_by(Account.parent_id)
            )
        ).all()
        parent_ids = {pid for pid, _ in rows if pid}

        # отбираем только свои main‑акки
        mains = (
            await sess.scalars(
                select(Account).where(
                    Account.parent_id.is_(None),
                    Account.users.any(UserAccountLink.user_id == owner.id),
                    Account.id.in_(parent_ids),
                )
            )
        ).all()

        # создаём пул
        pool = Pool(
            label=label,
            owner_id=owner.id,
            pool_type=PoolType.SUB_ACC_REQUIRED,
            is_active=False,
            status=PoolStatus.STOPPED,
        )
        sess.add(pool)
        await sess.flush()

        links = [PoolAccountLink(pool_id=pool.id, account_id=acc.id) for acc in mains]
        sess.add_all(links)
        await sess.commit()

        count = len(mains)

    await msg.answer(
        f"🆕 Пул «<b>{label}</b>» создан.\nДобавлено аккаунтов: <b>{count}</b>",
        parse_mode="HTML",
        reply_markup=confirm_pool_kb(pool.id),
    )


@pools_router.callback_query(F.data.startswith("pool_manage:"))
async def manage_pool(cb: CallbackQuery):
    """Меню управления конкретным пулом."""
    await cb.answer()
    pid = int(cb.data.split(":", 1)[1])

    async with pg.session_maker() as sess:
        pool = await sess.get(Pool, pid)
        if not pool:
            await cb.message.answer("❌ Пул не найден")
            return

    await cb.message.answer(
        f"<b>Пул:</b> {pool.label}\n" f"Статус: {'🚀' if pool.is_active else '⏸️'}",
        parse_mode="HTML",
        reply_markup=confirm_pool_kb(pid),
    )


@pools_router.callback_query(F.data.startswith("pool_run:"))
async def pool_run(cb: CallbackQuery):
    """Запуск пула."""
    await cb.answer()
    pid = int(cb.data.split(":", 1)[1])
    async with pg.session_maker() as sess:
        pool = await sess.get(Pool, pid)
        if pool:
            pool.is_active = True
            pool.status = PoolStatus.RUNNING
            await sess.commit()
            await cb.message.answer("✅ Пул запущен")
        else:
            await cb.message.answer("❌ Пул не найден")


@pools_router.callback_query(F.data.startswith("pool_stop:"))
async def pool_stop(cb: CallbackQuery):
    """Остановка пула."""
    await cb.answer()
    pid = int(cb.data.split(":", 1)[1])
    async with pg.session_maker() as sess:
        pool = await sess.get(Pool, pid)
        if pool:
            pool.is_active = False
            pool.status = PoolStatus.STOPPED
            await sess.commit()
            await cb.message.answer("🛑 Пул остановлен")
        else:
            await cb.message.answer("❌ Пул не найден")


@pools_router.callback_query(F.data.startswith("pool_update:"))
async def pool_update(cb: CallbackQuery):
    """Обновление списка аккаунтов в пуле."""
    await cb.answer()
    pid = int(cb.data.split(":", 1)[1])
    async with pg.session_maker() as sess:
        pool = await sess.get(Pool, pid)
        if not pool:
            await cb.message.answer("❌ Пул не найден")
            return

        current_ids = {link.account_id for link in pool.accounts}
        rows = (
            await sess.execute(
                select(Account.parent_id, func.count())
                .where(Account.parent_id.isnot(None))
                .group_by(Account.parent_id)
            )
        ).all()
        parent_ids = {pid for pid, _ in rows if pid}

        new_ids = set(
            await sess.scalars(
                select(Account.id).where(
                    Account.parent_id.is_(None),
                    Account.id.in_(parent_ids),
                )
            ).all()
        )

        to_add = new_ids - current_ids
        to_remove = current_ids - new_ids

        if to_add:
            sess.add_all(PoolAccountLink(pool_id=pid, account_id=i) for i in to_add)
        if to_remove:
            await sess.execute(
                delete(PoolAccountLink).where(
                    PoolAccountLink.pool_id == pid,
                    PoolAccountLink.account_id.in_(to_remove),
                )
            )
        await sess.commit()

    await cb.message.answer(
        f"♻️ Обновлено.\nДобавлено: {len(to_add)}\nУдалено: {len(to_remove)}"
    )


@pools_router.callback_query(F.data.startswith("pool_del:"))
async def pool_del(cb: CallbackQuery):
    """Удаление пула."""
    await cb.answer()
    pid = int(cb.data.split(":", 1)[1])
    async with pg.session_maker() as sess:
        await sess.execute(
            delete(PoolAccountLink).where(PoolAccountLink.pool_id == pid)
        )
        await sess.execute(delete(Pool).where(Pool.id == pid))
        await sess.commit()

    await cb.message.answer("❌ Пул удалён")
