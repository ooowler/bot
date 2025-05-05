from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger

from src.bot.features.accounts.keyboards import accounts_actions_keyboard
from src.bot.features.accounts.states import AccountsStates
from src.bot.triggers import Texts
from src.core.clients.exchanges.backpack.backpack import BackpackExchangeClient
from src.core.repositories import accounts as accounts_repo

router = Router()


@router.message(
    F.text == Texts.Accounts.BALANCE, StateFilter(AccountsStates.account_selected)
)
async def show_balance(message: Message, state: FSMContext) -> None:
    account_id: int | None = (await state.get_data()).get("account_id")
    if account_id is None:
        await message.answer(
            "Сначала выберите аккаунт.", reply_markup=accounts_actions_keyboard()
        )
        return

    acc = await accounts_repo.get_by_id(account_id)
    if not acc:
        await message.answer(
            "Аккаунт не найден.", reply_markup=accounts_actions_keyboard()
        )
        return

    client = BackpackExchangeClient(api_key=acc.api_key, api_secret=acc.api_secret)

    # ─── Баланс ────────────────────────────────────────────────
    try:
        balances = await client.get_balance()
    except Exception as e:
        logger.warning(f"Backpack balance error: {e}")
        balances = None

    # ─── Borrow/Lend позиции ──────────────────────────────────
    try:
        lend = await client.get_borrow_lend_positions()
    except Exception as e:
        logger.warning(f"Backpack lend error: {e}")
        lend = None

    parts: list[str] = []

    if balances is not None:
        bal_lines: list[str] = []
        for idx, (symbol, bal) in enumerate(balances.balances.items(), 1):
            part_text = ", ".join(
                p
                for p in (
                    f"available: {bal.available}" if bal.available else None,
                    f"locked: {bal.locked}" if bal.locked else None,
                    f"staked: {bal.staked}" if bal.staked else None,
                )
                if p
            )
            if part_text:
                bal_lines.append(f"{idx}. <b>{symbol}</b> — {part_text}")
        parts.append("<b>💰 Баланс аккаунта:</b>")
        parts.extend(bal_lines)
    else:
        parts.append("⚠️ Не удалось получить баланс")

    if lend is not None and lend.positions:
        lend_lines = [
            f"{idx}. <b>{p.symbol}</b> — quantity: {p.netExposureQuantity}, "
            f"notional: {p.netExposureNotional}$"
            for idx, p in enumerate(lend.positions, 1)
        ]
        parts.append("\n<b>📊 Borrow/Lend позиции:</b>")
        parts.extend(lend_lines)
    elif lend is None:
        parts.append("⚠️ Не удалось получить позиции borrow/lend")

    await message.answer(
        "\n".join(parts),
        parse_mode="HTML",
        reply_markup=accounts_actions_keyboard(),
    )
