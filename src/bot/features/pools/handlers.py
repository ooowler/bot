from aiogram import Router
from aiogram.filters import Command, StateFilter
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from src.bot.features.exchange.states import ExchangeStates

router = Router()


@router.message(Command("pools"), StateFilter(ExchangeStates.selected))
async def show_pools(msg: Message, state: FSMContext):
    data = await state.get_data()
    await msg.answer(f"Пулы для биржи {data['exchange']}")
