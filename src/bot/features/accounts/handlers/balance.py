from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger
from decimal import Decimal

from aiogram.exceptions import TelegramBadRequest
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
    data = await state.get_data()
    account_id: int | None = data.get("account_id")
    if account_id is None:
        return await message.answer(
            "Сначала выберите аккаунт.",
            reply_markup=accounts_actions_keyboard(),
        )

    client = await accounts_repo.get_backpack_client_by_account_id(account_id)
    if not client:
        return await message.answer(
            "Аккаунт не найден.",
            reply_markup=accounts_actions_keyboard(),
        )

    # Информируем пользователя
    await message.answer(
        "🕐 Делаю запрос в биржу…",
        reply_markup=accounts_actions_keyboard(),
    )

    # Параллельные запросы
    try:
        totals_resp = await client.get_total_token_quantities()
        tickers_resp = await client.get_tickers()
    except Exception as e:
        logger.warning(f"Backpack data error: {e}")
        return await message.answer(
            "⚠️ Ошибка при запросе к бирже, попробуйте позже.",
            reply_markup=accounts_actions_keyboard(),
        )

    # Собираем цены только для *_USDC пар
    price_map: dict[str, Decimal] = {
        t.symbol: Decimal(t.lastPrice)
        for t in tickers_resp.tickers
        if t.symbol.endswith("_USDC")
    }
    price_map["USDC_USDC"] = Decimal("1")

    # Собираем портфель (symbol, amount, value_usd)
    portfolio: list[tuple[str, Decimal, Decimal]] = []
    for symbol, amount in totals_resp.totals.items():
        pair = f"{symbol}_USDC"
        price = price_map.get(pair)
        if price is None:
            continue
        value_usd = amount * price
        portfolio.append((symbol, amount, value_usd))

    # Сортируем по убыванию USD
    portfolio.sort(key=lambda x: x[2], reverse=True)

    # Формируем итоговый текст
    if not portfolio:
        text = "Нет активных токенов для отображения."
    else:
        lines = [
            f"{idx}. <b>{symbol}</b>: {amount} (~{value_usd:.2f} $)"
            for idx, (symbol, amount, value_usd) in enumerate(portfolio, start=1)
        ]
        text = "<b>Баланс и оценка в USD:</b>\n" + "\n".join(lines)

    # Отправляем результат
    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=accounts_actions_keyboard(),
    )
