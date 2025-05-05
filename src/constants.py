from enum import StrEnum

METRICS_DB_PREFIX = "db_"


class Exchanges(StrEnum):
    BACKPACK = "backpack"

    @classmethod
    def has_value(cls, item: object) -> bool:
        return any(item == member.value for member in cls)
