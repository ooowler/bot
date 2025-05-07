# src/bot/features/accounts/handlers/order_market.py
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

router = Router()


def _format_result_html(res: dict) -> str:
    dumped = json.dumps(res, indent=2, ensure_ascii=False)
    return f"<pre>{html.escape(dumped)}</pre>"


@router.message(
    F.text == Texts.Accounts.MARKET_ORDER,
    StateFilter(AccountsStates.account_selected),
)
async def order_start(message: Message, state: FSMContext) -> None:
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Market (рыночный)")],
            [KeyboardButton(text="Limit (лимитный)")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await state.set_state(OrderStates.choose_side)
    await message.answer("Выберите тип ордера:", reply_markup=kb)


@router.message(StateFilter(OrderStates.choose_side))
async def order_choose_side(message: Message, state: FSMContext) -> None:
    text = message.text.strip().lower()
    if "market" in text:
        await state.update_data(order_type="Market")
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Купить")],
                [KeyboardButton(text="Продать")],
            ],
            resize_keyboard=True,
            one_time_keyboard=True,
        )
        await state.set_state(OrderStates.symbol)
        await message.answer(
            "Market-ордер: выберите сторону или введите пару:", reply_markup=kb
        )
    elif "limit" in text:
        await state.update_data(order_type="Limit")
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Купить")],
                [KeyboardButton(text="Продать")],
            ],
            resize_keyboard=True,
            one_time_keyboard=True,
        )
        await state.set_state(LimitOrderStates.limit_choose_side)
        await message.answer("Limit-ордер: выберите сторону:", reply_markup=kb)
    else:
        await message.answer(
            "Пожалуйста, выберите Market или Limit.", reply_markup=accounts_keyboard()
        )


@router.message(StateFilter(OrderStates.symbol))
async def market_symbol_or_side(message: Message, state: FSMContext) -> None:
    txt = message.text.strip()
    if txt.lower() in ("купить", "продать"):
        # это сторона
        side = "Bid" if txt.lower() == "купить" else "Ask"
        await state.update_data(order_side=side)
        await state.set_state(OrderStates.quantity)
        await message.answer("Введите количество:", reply_markup=accounts_keyboard())
    else:
        # это пара
        symbol = txt.upper()
        await state.update_data(order_symbol=symbol)
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Купить")],
                [KeyboardButton(text="Продать")],
            ],
            resize_keyboard=True,
            one_time_keyboard=True,
        )
        await state.set_state(OrderStates.symbol)
        await message.answer(
            f"Пара <b>{symbol}</b> принята. Теперь выберите сторону:",
            parse_mode="HTML",
            reply_markup=kb,
        )


@router.message(StateFilter(OrderStates.quantity))
async def market_quantity(message: Message, state: FSMContext) -> None:
    txt = message.text.strip()
    try:
        qty = str(Decimal(txt))
    except InvalidOperation:
        await message.answer(
            "❌ Некорректное число. Повторите ввод:", reply_markup=accounts_keyboard()
        )
        return

    data = await state.get_data()
    acc_id = data["account_id"]
    symbol = data["order_symbol"]
    side = data["order_side"]

    acc = await accounts_repo.get_by_id(acc_id)
    if not acc:
        await message.answer("❌ Аккаунт не найден.", reply_markup=accounts_keyboard())
        await state.clear()
        return

    client = BackpackExchangeClient(api_key=acc.api_key, api_secret=acc.api_secret)
    result = await client.create_order(
        symbol=symbol, side=side, quantity=qty, order_type="Market"
    )

    action = "покупка" if side == "Bid" else "продажа"
    await message.answer(
        f"⚡ Market-ордер ({action}) {symbol} выполнен:\n"
        + _format_result_html(result),
        parse_mode="HTML",
        reply_markup=accounts_actions_keyboard(),
    )
    await state.clear()


@router.message(StateFilter(LimitOrderStates.limit_choose_side))
async def limit_choose_side(message: Message, state: FSMContext) -> None:
    txt = message.text.strip().lower()
    if txt not in ("купить", "продать"):
        await message.answer(
            "Пожалуйста, выберите «Купить» или «Продать».",
            reply_markup=accounts_keyboard(),
        )
        return
    side = "Bid" if txt == "купить" else "Ask"
    await state.update_data(order_side=side)
    await state.set_state(LimitOrderStates.limit_symbol)
    await message.answer(
        "Введите торговую пару (например SOL_USDC):", reply_markup=accounts_keyboard()
    )


@router.message(StateFilter(LimitOrderStates.limit_symbol))
async def limit_symbol(message: Message, state: FSMContext) -> None:
    sym = message.text.strip().upper()
    await state.update_data(order_symbol=sym)
    await state.set_state(LimitOrderStates.limit_quantity)
    await message.answer(
        f"Сколько {sym}? Введите количество:", reply_markup=accounts_keyboard()
    )


@router.message(StateFilter(LimitOrderStates.limit_quantity))
async def limit_quantity(message: Message, state: FSMContext) -> None:
    txt = message.text.strip()
    try:
        qty = str(Decimal(txt))
    except InvalidOperation:
        await message.answer(
            "❌ Некорректное число. Повторите ввод:", reply_markup=accounts_keyboard()
        )
        return
    await state.update_data(order_quantity=qty)
    await state.set_state(LimitOrderStates.limit_price)
    await message.answer(
        "Укажите цену (например 1.2345):", reply_markup=accounts_keyboard()
    )


@router.message(StateFilter(LimitOrderStates.limit_price))
async def limit_price(message: Message, state: FSMContext) -> None:
    txt = message.text.strip()
    try:
        price = str(Decimal(txt))
    except InvalidOperation:
        await message.answer(
            "❌ Некорректная цена. Повторите ввод:", reply_markup=accounts_keyboard()
        )
        return

    data = await state.get_data()
    acc_id = data["account_id"]
    symbol = data["order_symbol"]
    side = data["order_side"]
    qty = data["order_quantity"]

    acc = await accounts_repo.get_by_id(acc_id)
    if not acc:
        await message.answer("❌ Аккаунт не найден.", reply_markup=accounts_keyboard())
        await state.clear()
        return

    client = BackpackExchangeClient(api_key=acc.api_key, api_secret=acc.api_secret)
    result = await client.create_order(
        symbol=symbol, side=side, quantity=qty, order_type="Limit", price=price
    )

    action = "покупка" if side == "Bid" else "продажа"
    await message.answer(
        f"⚡ Limit-ордер ({action}) {symbol} по цене {price} выполнен:\n"
        + _format_result_html(result),
        parse_mode="HTML",
        reply_markup=accounts_actions_keyboard(),
    )
    await state.clear()
