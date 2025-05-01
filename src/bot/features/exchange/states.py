from aiogram.fsm.state import StatesGroup, State


class ExchangeStates(StatesGroup):
    choosing = State()
    selected = State()
