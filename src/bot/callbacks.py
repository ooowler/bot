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


class ProxyCallbacks(StrEnum):
    INFO = "proxy_info"


class PoolsCallbacks(StrEnum):
    INFO = "pools_info"


class ExchangesCallbacks(StrEnum):
    BACKPACK = "exchanges_backpack"


@dataclass(frozen=True)
class Callbacks:
    User: UserCallbacks = UserCallbacks
    Accounts: AccountsCallbacks = AccountsCallbacks
    Proxy: ProxyCallbacks = ProxyCallbacks
    Pools: PoolsCallbacks = PoolsCallbacks
    Exchanges: ExchangesCallbacks = ExchangesCallbacks
