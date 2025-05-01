from enum import Enum


class Chain(str, Enum):
    EQUALS_MONEY = "EqualsMoney"
    SOLANA = "solana"
    ETHEREUM = "ethereum"
    BITCOIN = "bitcoin"
