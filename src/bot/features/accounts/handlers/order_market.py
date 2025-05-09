import json
import html
from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

from src.bot.features.accounts.keyboards import (
    accounts_keyboard,
    accounts_actions_keyboard,
)
from src.bot.features.accounts.states import (
    AccountsStates,
    OrderStates,
    LimitOrderStates,
)
from src.bot.triggers import Texts
from src.core.repositories import accounts as accounts_repo
from src.core.clients.exchanges.backpack.backpack import BackpackExchangeClient
from loguru import logger

router = Router()


def get_order_type_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Market (рыночный)")],
            [KeyboardButton(text="Limit (лимитный)")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


async def reset_to_account_selected(state: FSMContext) -> None:
    data = await state.get_data()
    account_id = data.get("account_id")
    await state.clear()
    if account_id is not None:
        await state.update_data(account_id=account_id)
        await state.set_state(AccountsStates.account_selected)


@router.message(
    F.text == Texts.Accounts.MARKET_ORDER,
    StateFilter(AccountsStates.account_selected),
)
async def order_start(message: Message, state: FSMContext) -> None:
    await state.set_state(OrderStates.choose_side)
    await message.answer(
        "Выберите тип ордера:",
        reply_markup=get_order_type_keyboard(),
    )


# --- Market flow ---
@router.message(F.text == "Market (рыночный)", StateFilter(OrderStates.choose_side))
async def market_order_symbol(message: Message, state: FSMContext) -> None:
    await state.update_data(order_type="Market")
    await state.set_state(OrderStates.symbol)
    await message.answer(
        "Market-ордер: введите торговую пару (например SOL_USDC):",
        reply_markup=accounts_keyboard(),
    )


@router.message(StateFilter(OrderStates.symbol))
async def market_order_side(message: Message, state: FSMContext) -> None:
    symbol = message.text.strip().upper()
    await state.update_data(order_symbol=symbol)
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Купить")],
            [KeyboardButton(text="Продать")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await state.set_state(OrderStates.side)
    await message.answer(
        f"Пара <b>{symbol}</b> сохранена. Теперь выберите сторону:",
        parse_mode="HTML",
        reply_markup=kb,
    )


@router.message(StateFilter(OrderStates.side))
async def market_order_quantity(message: Message, state: FSMContext) -> None:
    text = message.text.strip().lower()
    if text not in ("купить", "продать"):
        return await message.answer(
            "Пожалуйста, нажмите кнопку 'Купить' или 'Продать'.",
            reply_markup=accounts_keyboard(),
        )
    side = "Bid" if text == "купить" else "Ask"
    await state.update_data(order_side=side)
    await state.set_state(OrderStates.quantity)
    await message.answer(
        "Введите количество:",
        reply_markup=accounts_keyboard(),
    )


@router.message(StateFilter(OrderStates.quantity))
async def market_order_execute(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    symbol = data.get("order_symbol")
    side = data.get("order_side")
    try:
        qty = str(Decimal(message.text.strip()))
    except InvalidOperation:
        return await message.answer(
            "❌ Некорректное количество, введите число.",
            reply_markup=accounts_keyboard(),
        )
    acc_id = data.get("account_id")
    client = await accounts_repo.get_backpack_client_by_account_id(acc_id)
    if not client:
        await message.answer(
            "❌ Аккаунт не найден.",
            reply_markup=accounts_keyboard(),
        )
        await reset_to_account_selected(state)
        return
    try:
        await client.create_market_order(symbol=symbol, side=side, quantity=qty)
    except Exception as e:
        logger.error(f"Exception create_market_order: {e}")
        await message.answer(
            "❌ Не удалось создать маркет-ордер.",
            reply_markup=accounts_actions_keyboard(),
        )
        await reset_to_account_selected(state)
        return
    await message.answer(
        f"⚡ Market-ордер выполнен: {side} {qty} {symbol}",
        reply_markup=accounts_actions_keyboard(),
    )
    await reset_to_account_selected(state)


# --- Limit flow ---
@router.message(F.text == "Limit (лимитный)", StateFilter(OrderStates.choose_side))
async def limit_order_symbol(message: Message, state: FSMContext) -> None:
    await state.update_data(order_type="Limit")
    await state.set_state(LimitOrderStates.limit_symbol)
    await message.answer(
        "Limit-ордер: введите торговую пару (например SOL_USDC):",
        reply_markup=accounts_keyboard(),
    )


@router.message(StateFilter(LimitOrderStates.limit_symbol))
async def limit_order_side(message: Message, state: FSMContext) -> None:
    symbol = message.text.strip().upper()
    await state.update_data(order_symbol=symbol)
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Купить")],
            [KeyboardButton(text="Продать")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await state.set_state(LimitOrderStates.limit_side)
    await message.answer(
        f"Пара <b>{symbol}</b> сохранена. Теперь выберите сторону:",
        parse_mode="HTML",
        reply_markup=kb,
    )


@router.message(StateFilter(LimitOrderStates.limit_side))
async def limit_order_quantity(message: Message, state: FSMContext) -> None:
    text = message.text.strip().lower()
    if text not in ("купить", "продать"):
        return await message.answer(
            "Пожалуйста, нажмите кнопку 'Купить' или 'Продать'.",
            reply_markup=accounts_keyboard(),
        )
    side = "Bid" if text == "купить" else "Ask"
    await state.update_data(order_side=side)
    await state.set_state(LimitOrderStates.limit_quantity)
    await message.answer(
        "Введите количество:",
        reply_markup=accounts_keyboard(),
    )


@router.message(StateFilter(LimitOrderStates.limit_quantity))
async def limit_order_price(message: Message, state: FSMContext) -> None:
    try:
        qty = str(Decimal(message.text.strip()))
    except InvalidOperation:
        return await message.answer(
            "❌ Некорректное количество, повторите ввод.",
            reply_markup=accounts_keyboard(),
        )
    await state.update_data(order_quantity=qty)
    await state.set_state(LimitOrderStates.limit_price)
    await message.answer(
        "Укажите цену (например 1.2345):",
        reply_markup=accounts_keyboard(),
    )


@router.message(StateFilter(LimitOrderStates.limit_price))
async def limit_order_execute(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    symbol = data.get("order_symbol")
    side = data.get("order_side")
    qty = data.get("order_quantity")
    try:
        price = str(Decimal(message.text.strip()))
    except InvalidOperation:
        return await message.answer(
            "❌ Некорректная цена, повторите ввод.",
            reply_markup=accounts_keyboard(),
        )
    acc_id = data.get("account_id")
    client = await accounts_repo.get_backpack_client_by_account_id(acc_id)
    if not client:
        await message.answer(
            "❌ Аккаунт не найден.",
            reply_markup=accounts_keyboard(),
        )
        await reset_to_account_selected(state)
        return
    try:
        await client.create_limit_order(
            symbol=symbol, side=side, quantity=qty, price=price
        )
    except Exception:
        await message.answer(
            "❌ Не удалось создать лимит-ордер.",
            reply_markup=accounts_actions_keyboard(),
        )
        await reset_to_account_selected(state)
        return
    await message.answer(
        f"⚡ Limit-ордер выполнен: {side} {qty} {symbol} @ {price}",
        reply_markup=accounts_actions_keyboard(),
    )
    await reset_to_account_selected(state)
