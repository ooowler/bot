from decimal import Decimal
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from src.bot.callbacks import Callbacks
from src.bot.features.accounts.keyboards import accounts_actions_keyboard
from src.core.clients.databases.postgres import pg
from src.core.models import Account
from src.core.clients.exchanges.backpack.backpack import BackpackExchangeClient

router = Router()


@router.callback_query(
    F.data == Callbacks.Accounts.BALANCE,
)
async def show_balance(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    data = await state.get_data()
    account_id = data.get("account_id")

    async with pg.session_maker() as session:
        stmt = select(Account).where(Account.id == account_id)
        acc = await session.scalar(stmt)

    if not acc:
        await cb.message.answer(
            "Аккаунт не найден", reply_markup=accounts_actions_keyboard()
        )
        return

    client = BackpackExchangeClient(
        api_key=acc.api_key,
        api_secret=acc.api_secret,
    )

    balances = await client.get_balance()
    lend = await client.get_borrow_lend_positions()

    lines = []
    for idx, (symbol, bal) in enumerate(balances.balances.items(), start=1):
        parts = ", ".join(
            part
            for part in (
                f"available: {bal.available}" if bal.available else None,
                f"locked: {bal.locked}" if bal.locked else None,
                f"staked: {bal.staked}" if bal.staked else None,
            )
            if part
        )
        if parts:
            lines.append(f"{idx}. <b>{symbol}</b> — {parts}")

    lend_lines: list[str] = []
    for idx, pos in enumerate(lend.positions, start=1):
        sym = pos.symbol
        qty = pos.netExposureQuantity
        notional = pos.netExposureNotional
        lend_lines.append(
            f"{idx}. <b>{sym}</b> — quantity: {qty}, notional: {notional}$"
        )

    message = "<b>💰 Баланс аккаунта:</b>" + "\n".join(lines)
    if lend_lines:
        message += "\n\n<b>📊 Borrow/Lend позиции:</b>" + "\n".join(lend_lines)

    await cb.message.answer(
        message, parse_mode="HTML", reply_markup=accounts_actions_keyboard()
    )
