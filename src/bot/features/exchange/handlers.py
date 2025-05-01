from aiogram import Router
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from src.bot.features.exchange.states import ExchangeStates
from src.bot.features.exchange.keyboards import exchange_keyboard

router = Router()


@router.message(Command("select_exchange"))
async def select_exchange(msg: Message, state: FSMContext):
    data = await state.get_data()
    await msg.answer(
        f"Выберите биржу (Сейчас выбрано: {data.get('exchange')})",
        reply_markup=exchange_keyboard(["backpack", "binance"]),
    )
    await state.set_state(ExchangeStates.choosing)


@router.callback_query(StateFilter(ExchangeStates.choosing))
async def choose_exchange(cb: CallbackQuery, state: FSMContext):
    name = cb.data.split(":", 1)[1]
    await state.update_data(exchange=name)
    await state.set_state(ExchangeStates.selected)
    await cb.message.edit_text(f"Биржа {name} выбрана")
