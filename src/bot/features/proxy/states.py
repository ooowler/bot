from aiogram.fsm.state import StatesGroup, State


class ProxyStates(StatesGroup):
    viewing = State()
    adding = State()
    deleting = State()
