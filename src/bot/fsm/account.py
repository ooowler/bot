from aiogram.fsm.state import StatesGroup, State


class AddAccountStates(StatesGroup):
    enter_pubkey = State()
    enter_privkey = State()
