from aiogram.fsm.state import StatesGroup, State


class AccountsStates(StatesGroup):
    waiting_api_key_or_name = State()
