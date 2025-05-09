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
        CONFIRM = "proxy_confirm"
        CANCEL = "proxy_cancel"

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
        ADD_CSV = "Добавить аккаунты через csv"
        DELETE = "Удалить аккаунт"
        STATS = "Статистика по аккаунтам"
        BALANCE = "Получить баланс"
        ORDER = "Выполнить ордер"
        MARKET_ORDER = "Маркет-ордер"
        TRANSFER = "Перевести средства"
        PROXY_CHECK = "Проверить прокси"
        PROXY_CHANGE = "Сменить прокси"

    class Pools(StrEnum):
        HOME = "Пулы"

    class Proxy(StrEnum):
        HOME = "Прокси"
        ADD = "Добавить Прокси"
        STATS = "Статистика по прокси"
        DELETE = "Удалить прокси"

    class Friends(StrEnum):
        HOME = "Друзья"
        ADD = "Добавить друга"


class Commands:
    class Home(StrEnum):
        START = "start"
        REFRESH = "refresh"
        HELP = "help"
