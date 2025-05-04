from aiogram.fsm.state import StatesGroup, State


class AccountsStates(StatesGroup):
    waiting_api_key_or_name = State()
    account_selected = State()

    waiting_api_key_or_name_to_delete = State()

    import_csv = State()

    adding_name = State()
    adding_api_key = State()
    adding_api_secret = State()
    adding_country = State()
    adding_deposit = State()
