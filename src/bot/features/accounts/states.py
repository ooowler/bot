from aiogram.fsm.state import StatesGroup, State


class AccountsStates(StatesGroup):
    creating = State()
    deleting = State()
