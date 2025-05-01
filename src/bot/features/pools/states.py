from aiogram.fsm.state import StatesGroup, State


class PoolsStates(StatesGroup):
    selecting = State()
    creating = State()
    deleting = State()
