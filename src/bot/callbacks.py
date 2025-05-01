from enum import StrEnum


class Callbacks:
    class User(StrEnum):
        SETTINGS = "user_settings"

    class Accounts(StrEnum):
        INFO = "accounts_info"
        ADD = "accounts_add"
        SHOW_ONE = "accounts_show_one"
        GET_BALANCE = "accounts_get_balance"
        EXECUTE_ORDER = "accounts_execute_order"
        DELETE = "accounts_delete"

    class Proxy(StrEnum):
        INFO = "proxy_info"
        ADD = "proxy_add"

    class Pools(StrEnum):
        INFO = "pools_info"
        SHOW = "pools_show"
        ADD = "pools_add"
        RUN = "pools_run"
        STOP = "pools_stop"
        UPDATE = "pools_update"
        DEL = "pools_del"

    class Exchanges(StrEnum):
        BACKPACK = "exchanges_backpack"
