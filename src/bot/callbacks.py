from enum import StrEnum
from dataclasses import dataclass


class UserCallbacks(StrEnum):
    SETTINGS = "user_settings"


class AccountsCallbacks(StrEnum):
    INFO = "accounts_info"
    ADD = "accounts_add"
    SHOW_ONE = "accounts_show_one"
    GET_BALANCE = "accounts_get_balance"
    EXECUTE_ORDER = "accounts_execute_order"
    DELETE = "accounts_delete"


class ProxyCallbacks(StrEnum):
    INFO = "proxy_info"
    ADD = "proxy_add"


class PoolsCallbacks(StrEnum):
    INFO = "pools_info"
    SHOW = "pools_show"
    ADD = "pools_add"
    RUN = "pools_run"
    STOP = "pools_stop"
    UPDATE = "pools_update"
    DEL = "pools_del"


class ExchangesCallbacks(StrEnum):
    BACKPACK = "exchanges_backpack"


@dataclass(frozen=True)
class Callbacks:
    User: UserCallbacks = UserCallbacks
    Accounts: AccountsCallbacks = AccountsCallbacks
    Proxy: ProxyCallbacks = ProxyCallbacks
    Pools: PoolsCallbacks = PoolsCallbacks
    Exchanges: ExchangesCallbacks = ExchangesCallbacks
