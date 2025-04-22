from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from sqlalchemy import select, func

from bot.services.pools.subacc_trading_strategy import _load_proxy_and_fake
from src.core.clients.databases.postgres import pg
from src.core.models.base import Account, DepositAddress
from src.bot.callbacks import Callbacks
from src.bot.keyboards.start.start import get_welcome_keyboard

view_account = Router()

# ───────────────────────────── KEYBOARDS ──────────────────────────────


def get_account_actions_kb() -> InlineKeyboardMarkup:
    """Клавиатура без id — выбор действия выполняется через FSM."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📊 Баланс", callback_data=Callbacks.Accounts.GET_BALANCE
                )
            ],
            [
                InlineKeyboardButton(
                    text="🛒 Выполнить ордер",
                    callback_data=Callbacks.Accounts.EXECUTE_ORDER,
                )
            ],
        ]
    )


# ───────────────────────────── STATES ────────────────────────────────
class ViewAccount(StatesGroup):
    waiting_api_key = State()  # ждём API‑key


class AccountActions(StatesGroup):
    choose = State()  # выбран аккаунт, ждём действие


# ─────────────────── старт: «Посмотреть аккаунт» ─────────────────────
@view_account.callback_query(F.data == Callbacks.Accounts.SHOW_ONE)
async def ask_api_key(cb: CallbackQuery, state: FSMContext):
    await state.set_state(ViewAccount.waiting_api_key)
    await cb.message.edit_text(
        "✉️ Пришлите PUBLIC API‑KEY аккаунта, о котором хотите узнать."
    )
    await cb.answer()


# ─────────── получили ключ, показали инфу и действия ────────────────
@view_account.message(ViewAccount.waiting_api_key)
async def show_account_info(msg: Message, state: FSMContext):
    api_key = msg.text.strip()

    async with pg.session_maker() as session:
        acc_stmt = select(Account).where(Account.api_key == api_key)
        account: Account | None = (await session.execute(acc_stmt)).scalar_one_or_none()

        if account is None:
            await state.clear()
            await msg.answer(
                "❌ Аккаунт с таким ключом не найден.",
                reply_markup=get_welcome_keyboard(),
            )
            return

        sub_count = await session.scalar(
            select(func.count())
            .select_from(Account)
            .where(Account.parent_id == account.id)
        )
        deps = (
            await session.scalars(
                select(DepositAddress).where(DepositAddress.account_id == account.id)
            )
        ).all()

    dep_lines = [f"{d.chain.value.upper()}: `{d.address}`" for d in deps] or ["—"]
    text = (
        "<b>Информация об аккаунте</b>\n"
        f"ID: <code>{account.id}</code>\n"
        f"Тип: {'SUB' if account.is_sub else 'MAIN'}\n"
        f"Страна: {account.country or '—'}\n"
        f"Sub‑аккаунтов: {sub_count}\n"
        f"Создан: {account.created_at:%Y-%m-%d %H:%M:%S} UTC\n\n"
        "<b>Депозитные адреса</b>:\n" + "\n".join(dep_lines)
    )

    # сохраняем выбранный аккаунт и переходим в состояние выбора действия
    await state.update_data(account_id=account.id)
    await state.set_state(AccountActions.choose)

    await msg.answer(text, parse_mode="HTML", reply_markup=get_account_actions_kb())


# ──────────────────── действие «Баланс» ─────────────────────────────
@view_account.callback_query(
    AccountActions.choose, F.data == Callbacks.Accounts.GET_BALANCE
)
async def show_balance(cb: CallbackQuery, state: FSMContext):
    """Выводит баланс + ленд через готовый метод клиента."""
    from src.core.clients.exchanges.backpack.backpack import BackpackExchangeClient

    data = await state.get_data()
    account_id: int | None = data.get("account_id")
    if account_id is None:
        await cb.answer("Ошибка state", show_alert=True)
        return

    async with pg.session_maker() as session:
        acc: Account | None = await session.get(Account, account_id)
    if acc is None:
        await cb.answer("Аккаунт не найден", show_alert=True)
        return

    proxy_url, headers, cookies = await _load_proxy_and_fake(acc.id)
    client = BackpackExchangeClient(
        base_url="https://api.backpack.exchange/",
        api_key=acc.api_key,
        api_secret=acc.api_secret,
        proxy_url=proxy_url,
        fake_headers=headers,
        cookies=cookies,
    )

    tokens = await client.get_balances_usd()  # готовый агрегационный метод
    if not tokens:
        await cb.answer()
        await cb.message.answer("Баланс пуст")
        return

    lines = [
        f"{i+1}. <b>{t['token']}</b> — {t['quantity']:.5f} ≈ {t['usd']:.2f}$"
        for i, t in enumerate(tokens)
    ]
    total = sum(t["usd"] for t in tokens)

    message = "<b>💰 Баланс аккаунта:</b>\n"
    message += "\n".join(lines)
    message += f"\n\n<b>Итого:</b> <code>{total:.2f}$</code>"

    await cb.answer()
    await cb.message.answer(message, parse_mode="HTML")


@view_account.callback_query(
    AccountActions.choose, F.data == Callbacks.Accounts.EXECUTE_ORDER
)
async def execute_order(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    account_id = data.get("account_id")
    if account_id is None:
        await cb.answer("Ошибка state", show_alert=True)
        return

    await cb.answer()
    await cb.message.answer("🛒 Ордер (пока заглушка) выставлен!")


async def execute_order(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    account_id = data.get("account_id")
    if account_id is None:
        await cb.answer("Ошибка state", show_alert=True)
        return

    await cb.answer()
    await cb.message.answer("🛒 Ордер (пока заглушка) выставлен!")


async def execute_order(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    account_id = data.get("account_id")
    if account_id is None:
        await cb.answer("Ошибка state", show_alert=True)
        return

    # здесь будет логика выставления ордера
    await cb.answer()
    await cb.message.answer("🛒 Ордер (пока заглушка) выставлен!")


async def execute_order(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    account_id = data.get("account_id")
    if account_id is None:
        await cb.answer("Ошибка state", show_alert=True)
        return

    # здесь будет логика выставления ордера
    await cb.answer()
    await cb.message.answer("🛒 Ордер (пока заглушка) выставлен!")
