from aiogram.fsm.state import StatesGroup, State


class AddAccount(StatesGroup):
    waiting_api_key = State()
    waiting_api_secret = State()
    waiting_country = State()
    waiting_wallet_tag = State()
    waiting_deposit_sol = State()
    waiting_parent_id = State()
