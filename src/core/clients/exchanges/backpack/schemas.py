from pydantic import BaseModel
from decimal import Decimal


class TokenBalance(BaseModel):
    available: Decimal
    locked: Decimal
    staked: Decimal


class BalancesResponse(BaseModel):
    balances: dict[str, TokenBalance]


class BorrowLendPosition(BaseModel):
    netExposureNotional: Decimal
    netExposureQuantity: Decimal
    symbol: str


class BorrowLendPositionsResponse(BaseModel):
    positions: list[BorrowLendPosition]
