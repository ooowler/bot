from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from src.bot.callbacks import Callbacks
from src.bot.features.accounts.keyboards import accounts_keyboard
from src.bot.features.exchange.keyboards import exchange_keyboard
from src.bot.features.exchange.states import ExchangeStates

router = Router()


@router.callback_query(
    F.data == Callbacks.Accounts.HOME, StateFilter(ExchangeStates.selected)
)
async def accounts_callback(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    data = await state.get_data()
    await cb.message.answer(
        f"Аккаунты для биржи {data['exchange']}", reply_markup=accounts_keyboard()
    )


@router.callback_query(
    F.data == Callbacks.Accounts.HOME, ~StateFilter(ExchangeStates.selected)
)
async def accounts_no_exchange(cb: CallbackQuery, state: FSMContext):
    await state.set_state(ExchangeStates.choosing)
    await cb.message.answer("Сначала выберите биржу", reply_markup=exchange_keyboard())
