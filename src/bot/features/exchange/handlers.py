from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from src.bot.features.accounts.keyboards import accounts_keyboard
from src.constants import Exchanges
from src.bot.triggers import Callbacks, Texts
from src.bot.features.home.keyboards import main_menu_keyboard
from src.bot.features.exchange.states import ExchangeStates

from src.bot.features.exchange.keyboards import exchange_keyboard

router = Router()


@router.message(StateFilter(ExchangeStates.choosing))
async def choose_exchange(message: Message, state: FSMContext):
    name = message.text

    if not Exchanges.has_value(name):
        await message.answer(
            "Пожалуйста, выберите биржу из списка:", reply_markup=exchange_keyboard()
        )
        return

    await state.set_state(ExchangeStates.selected)
    await state.update_data(exchange=name)

    await message.answer(f"Биржа {name} выбрана ✅", reply_markup=accounts_keyboard())


@router.message(F.text == Texts.Accounts.HOME)
async def accounts_select_exchange(message: Message, state: FSMContext):
    await state.set_state(ExchangeStates.choosing)
    await message.answer("Выберите биржу", reply_markup=exchange_keyboard())
