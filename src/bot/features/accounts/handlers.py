from aiogram import Router
from aiogram.filters import Command, StateFilter
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from src.bot.features.exchange.states import ExchangeStates

router = Router()


@router.message(Command("accounts"), StateFilter(ExchangeStates.selected))
async def show_accounts(msg: Message, state: FSMContext):
    data = await state.get_data()
    await msg.answer(f"Аккаунты для биржи {data['exchange']}")
