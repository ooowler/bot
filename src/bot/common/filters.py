from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from src.bot.features.exchange.states import ExchangeStates


class IsExchangeSelected(BaseFilter):
    async def __call__(self, event: Message | CallbackQuery, state: FSMContext) -> bool:
        return await state.get_state() == ExchangeStates.selected
