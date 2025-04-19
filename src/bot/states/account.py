from aiogram.fsm.state import StatesGroup, State


class AddAccount(StatesGroup):
    public_key = State()
    secret_key = State()
    exchange = State()


class ExecuteAccount(StatesGroup):
    public_key = State()
    secret_key = State()
    exchange = State()
