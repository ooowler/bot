from enum import StrEnum


class Exchanges(StrEnum):
    BACKPACK = "backpack"

    @classmethod
    def has_value(cls, item: object) -> bool:
        return any(item == member.value for member in cls)
