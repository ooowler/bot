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


class Texts:
    class Accounts(StrEnum):
        HOME = "Аккаунты"
        FIND = "Найти аккаунт"
        ADD = "Добавить аккаунт"
        DELETE = "Удалить аккаунт"
        STATS = "Получить статистику по всем аккаунтами"
        BALANCE = "Получить баланс"
        ORDER = "Выполнить ордер"

    class Pools(StrEnum):
        HOME = "Пулы"

    class Proxy(StrEnum):
        HOME = "Прокси"


class Commands:
    class Home(StrEnum):
        START = "start"
        REFRESH = "refresh"
        HELP = "help"
