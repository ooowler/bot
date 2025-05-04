from enum import StrEnum


class Callbacks:
    class User(StrEnum):
        SETTINGS = "user_settings"

    class Accounts(StrEnum):
        HOME = "accounts_home"
        INFO = "accounts_info"
        FIND = "accounts_find"
        ADD = "accounts_add"
        SHOW_ONE = "accounts_show_one"
        BALANCE = "accounts_balance"
        GET_BALANCE = "accounts_get_balance"
        EXECUTE_ORDER = "accounts_execute_order"
        DELETE = "accounts_delete"

    class Proxy(StrEnum):
        HOME = "proxy_home"
        INFO = "proxy_info"
        ADD = "proxy_add"

    class Pools(StrEnum):
        HOME = "proxy_home"
        INFO = "pools_info"
        SHOW = "pools_show"
        ADD = "pools_add"
        RUN = "pools_run"
        STOP = "pools_stop"
        UPDATE = "pools_update"
        DEL = "pools_del"

    class Exchanges(StrEnum):
        SELECT = "exchanges_select"
        BACKPACK = "exchanges_backpack"
