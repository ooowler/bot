from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from src.bot.triggers import Texts
from src.bot.features.accounts.keyboards import accounts_keyboard
from src.bot.features.exchange.keyboards import exchange_keyboard
from src.bot.features.exchange.states import ExchangeStates

router = Router()


@router.message(
    F.text == Texts.Accounts.HOME.value, StateFilter(ExchangeStates.selected)
)
async def accounts_callback(message: Message, state: FSMContext):
    data = await state.get_data()
    await message.answer(
        f"Аккаунты для биржи {data['exchange']}", reply_markup=accounts_keyboard()
    )


@router.message(
    F.text == Texts.Accounts.HOME.value, ~StateFilter(ExchangeStates.selected)
)
async def accounts_no_exchange(message: Message, state: FSMContext):
    await state.set_state(ExchangeStates.choosing)
    await message.answer("Сначала выберите биржу", reply_markup=exchange_keyboard())
