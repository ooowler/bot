from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from src.bot.callbacks import Callbacks
from src.bot.features.home.keyboards import main_menu_keyboard
from src.bot.features.exchange.states import ExchangeStates

from src.bot.features.exchange.keyboards import exchange_keyboard

router = Router()


@router.callback_query(StateFilter(ExchangeStates.choosing))
async def choose_exchange(cb: CallbackQuery, state: FSMContext):
    name = cb.data.split("=", 1)[1]
    await state.update_data(exchange=name)
    await state.set_state(ExchangeStates.selected)
    await cb.message.edit_text(
        f"Биржа {name} выбрана", reply_markup=main_menu_keyboard()
    )


@router.callback_query(
    F.data == Callbacks.Exchanges.SELECT,
)
async def accounts_select_exchange(cb: CallbackQuery, state: FSMContext):
    await state.set_state(ExchangeStates.choosing)
    await cb.message.answer("Сначала выберите биржу", reply_markup=exchange_keyboard())
