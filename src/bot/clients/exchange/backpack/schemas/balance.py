from pydantic import BaseModel, Field
from typing import Dict


class TokenBalance(BaseModel):
    native: float = Field(..., description="Количество в нативной валюте (например, 0.01 BTC)")
    USD: float = Field(..., description="Стоимость в долларах")


class BalanceResponse(BaseModel):
    balance: Dict[str, TokenBalance]
