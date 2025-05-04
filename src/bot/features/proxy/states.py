from aiogram.fsm.state import StatesGroup, State


class ProxyStates(StatesGroup):
    adding = State()
    deleting_country = State()
    deleting_amount = State()
