from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from src.bot.triggers import Texts
from src.bot.features.accounts.keyboards import accounts_actions_keyboard
from src.core.clients.databases.postgres import pg
from src.core.models import Account
from src.core.clients.exchanges.backpack.backpack import BackpackExchangeClient
from src.bot.features.accounts.states import AccountsStates
from aiogram.filters import StateFilter

router = Router()


@router.message(
    F.text == Texts.Accounts.BALANCE, StateFilter(AccountsStates.account_selected)
)
async def show_balance(message: Message, state: FSMContext):
    data = await state.get_data()
    account_id = data.get("account_id")

    async with pg.session_maker() as session:
        stmt = select(Account).where(Account.id == account_id)
        acc = await session.scalar(stmt)

    if not acc:
        await message.answer(
            "Аккаунт не найден", reply_markup=accounts_actions_keyboard()
        )
        return

    client = BackpackExchangeClient(api_key=acc.api_key, api_secret=acc.api_secret)

    try:
        balances = await client.get_balance()
    except Exception as e:
        balances = None

    try:
        lend = await client.get_borrow_lend_positions()
    except Exception as e:
        lend = None

    parts = []

    if balances is not None:
        lines = []
        for idx, (symbol, bal) in enumerate(balances.balances.items(), start=1):
            parts_list = ", ".join(
                part
                for part in (
                    f"available: {bal.available}" if bal.available else None,
                    f"locked: {bal.locked}" if bal.locked else None,
                    f"staked: {bal.staked}" if bal.staked else None,
                )
                if part
            )
            if parts_list:
                lines.append(f"{idx}. <b>{symbol}</b> — {parts_list}")
        parts.append("<b>💰 Баланс аккаунта:</b>")
        parts.extend(lines)
    else:
        parts.append(f"⚠️ Не удалось получить баланс")

    if lend is not None:
        lend_lines = []
        for idx, pos in enumerate(lend.positions, start=1):
            lend_lines.append(
                f"{idx}. <b>{pos.symbol}</b> — quantity: {pos.netExposureQuantity}, notional: {pos.netExposureNotional}$"
            )
        if lend_lines:
            parts.append("\n<b>📊 Borrow/Lend позиции:</b>")
            parts.extend(lend_lines)
    else:
        parts.append(f"⚠️ Не удалось получить позиции borrow/lend")

    await message.answer(
        "\n".join(parts), parse_mode="HTML", reply_markup=accounts_actions_keyboard()
    )
