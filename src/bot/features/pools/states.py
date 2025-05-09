from aiogram.fsm.state import StatesGroup, State


class PoolStates(StatesGroup):
    selecting = State()
    menu = State()
    create_label = State()
    add_pool_id = State()
    add_account_id = State()
    remove_pool_id = State()
    remove_account_id = State()
    list_accounts_pool_id = State()
