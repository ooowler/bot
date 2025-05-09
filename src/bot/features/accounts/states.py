from aiogram.fsm.state import StatesGroup, State


class AccountsStates(StatesGroup):
    waiting_api_key_or_name = State()
    selecting_account = State()
    account_selected = State()

    waiting_api_key_or_name_to_delete = State()

    import_csv = State()

    find_mode = State()

    adding_name = State()
    adding_api_key = State()
    adding_api_secret = State()
    adding_country = State()
    adding_deposit = State()


class OrderStates(StatesGroup):
    choose_side = State()  # выбор Buy или Sell
    symbol = State()  # ждём ввода торговой пары
    quantity = State()  # ждём ввода количества
    price = State()  # новое состояние для ввода цены лимит-ордера
    side = State()


class LimitOrderStates(StatesGroup):
    limit_choose_side = State()
    limit_symbol = State()
    limit_quantity = State()
    limit_price = State()
    limit_side = State()


class TransferStates(StatesGroup):
    choosing_target = State()  # выбор аккаунта получателя
    entering_amount = State()  # ввод суммы для перевода
    confirming = State()  # подтверждение перевода(StatesGroup):
    limit_choose_side = State()
    limit_symbol = State()
    limit_quantity = State()
    limit_price = State()
