from pydantic import BaseModel
from decimal import Decimal
from datetime import datetime


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


class TotalTokenQuantitiesResponse(BaseModel):
    totals: dict[str, Decimal]


class WithdrawalResponse(BaseModel):
    accountIdentifier: str | None
    bankIdentifier: str | None
    bankName: str | None
    blockchain: str
    clientId: str | None
    createdAt: datetime
    fee: Decimal
    fiatFee: str | None
    fiatState: str | None
    fiatSymbol: str | None
    id: int
    identifier: str | None
    isInternal: bool
    providerId: str | None
    quantity: Decimal
    status: str
    subaccountId: str | None
    symbol: str
    toAddress: str
    transactionHash: str | None


class OrderResponseBase(BaseModel):
    clientId: str | None
    createdAt: int
    executedQuantity: str
    executedQuoteQuantity: str | None
    id: str
    orderType: str
    quantity: str
    reduceOnly: bool | None
    relatedOrderId: str | None
    selfTradePrevention: str | None
    side: str
    status: str
    symbol: str
    timeInForce: str
    stopLossLimitPrice: str | None
    stopLossTriggerBy: str | None
    stopLossTriggerPrice: str | None
    takeProfitLimitPrice: str | None
    takeProfitTriggerBy: str | None
    takeProfitTriggerPrice: str | None
    triggerBy: str | None
    triggerPrice: str | None
    triggerQuantity: str | None
    triggeredAt: str | None


class LimitOrderResponse(OrderResponseBase):
    postOnly: bool
    price: str


class MarketOrderResponse(OrderResponseBase):
    quoteQuantity: str


class OpenOrdersResponse(BaseModel):
    orders: list[OrderResponseBase]


class MarketSaleResult(BaseModel):
    symbol: str
    success: bool
    order: MarketOrderResponse | None
    error: str | None


class ConvertAllToUsdcResponse(BaseModel):
    results: list[MarketSaleResult]


class AccountInfoResponse(BaseModel):
    """
    Модель ответа метода get_account_info.
    """

    autoBorrowSettlements: bool
    autoLend: bool
    autoRealizePnl: bool
    autoRepayBorrows: bool
    borrowLimit: str
    futuresMakerFee: str
    futuresTakerFee: str
    leverageLimit: str
    limitOrders: int
    liquidating: bool
    positionLimit: str
    spotMakerFee: str
    spotTakerFee: str
    triggerOrders: int


class Ticker(BaseModel):
    firstPrice: str
    high: str
    lastPrice: str
    low: str
    priceChange: str
    priceChangePercent: str
    quoteVolume: str
    symbol: str
    trades: str
    volume: str


class TickersResponse(BaseModel):
    tickers: list[Ticker]
