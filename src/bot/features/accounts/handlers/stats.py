from datetime import datetime
from aiogram import F, Router
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from src.bot.features.accounts.keyboards import accounts_keyboard
from src.bot.triggers import Texts
from src.core.repositories import accounts as acc_repo

router = Router()


def _stats_text(accounts: list["Account"]) -> str:
    total = len(accounts)
    subs = sum(1 for a in accounts if a.parent_id)
    countries = sorted({a.country for a in accounts if a.country})
    exchanges = sorted({a.exchange for a in accounts if a.exchange})
    dates = [a.created_at for a in accounts if a.created_at]
    earliest = min(dates) if dates else None
    latest = max(dates) if dates else None

    lines = [
        "📊 Статистика аккаунтов:",
        f"Всего аккаунтов: {total}",
        f"Всего субаккаунтов: {subs}",
        f"Страны: {', '.join(countries) or '—'}",
        f"Биржи: {', '.join(exchanges) or '—'}",
    ]
    if earliest:
        lines.append(f"Первый аккаунт: {earliest:%Y-%m-%d}")
    if latest:
        lines.append(f"Последний аккаунт: {latest:%Y-%m-%d}")
    return "\n".join(lines)


# ───────── ШАГ 1: выбор фильтра ─────────
@router.message(F.text == Texts.Accounts.STATS)
async def accounts_stats_choose_filter(message: Message) -> None:
    my_tid = message.from_user.id

    friends = await acc_repo.confirmed_friends_with_username(my_tid)
    if not friends:
        # друзей нет → сразу «мои» аккаунты
        accounts = await acc_repo.fetch_accounts([my_tid])
        await message.answer(_stats_text(accounts), reply_markup=accounts_keyboard())
        return

    # формируем инлайн‑клаву
    buttons: list[InlineKeyboardButton] = [
        InlineKeyboardButton(text="🔹 Мои", callback_data=f"accstats:{my_tid}"),
        InlineKeyboardButton(text="👥 Все", callback_data="accstats:all"),
    ]
    for tid, uname in friends:
        uname = uname or str(tid)
        buttons.append(
            InlineKeyboardButton(text=f"👤 @{uname}", callback_data=f"accstats:{tid}")
        )

    kb = InlineKeyboardMarkup(inline_keyboard=[[b] for b in buttons])
    await message.answer("Чьи аккаунты показать?", reply_markup=kb)


# ───────── ШАГ 2: показать статистику ─────────
@router.callback_query(F.data.startswith("accstats:"))
async def accounts_stats_show(cb: CallbackQuery) -> None:
    my_tid = cb.from_user.id
    _, suffix = cb.data.split(":", 1)

    if suffix == "all":
        tids = [my_tid] + await acc_repo.confirmed_friend_ids(my_tid)
    else:
        tids = [int(suffix)]

    accounts = await acc_repo.fetch_accounts(tids)

    await cb.message.edit_text("Фильтр применён ✅")
    await cb.answer()
    await cb.message.answer(_stats_text(accounts), reply_markup=accounts_keyboard())
