from aiogram import Router
from aiogram.filters import Command, StateFilter
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from src.bot.features.exchange.states import ExchangeStates

router = Router()


@router.message(Command("proxy"), StateFilter(ExchangeStates.selected))
async def show_proxy(msg: Message, state: FSMContext):
    data = await state.get_data()
    await msg.answer(f"Прокси для биржи {data['exchange']}")
