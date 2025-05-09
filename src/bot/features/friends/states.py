from aiogram.fsm.state import StatesGroup, State


class FriendStates(StatesGroup):
    menu = State()
    waiting_add_username = State()
    waiting_remove_username = State()
