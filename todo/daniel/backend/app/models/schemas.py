from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class StockInfo(BaseModel):
    symbol: str
    name: str | None = None
    market: str | None = None
    sector: str | None = None
    industry: str | None = None
    currency: str | None = None
    exchange: str | None = None
    market_cap: float | None = None
    pe: float | None = None
    pb: float | None = None
    dividend_yield: float | None = None
    eps: float | None = None
    summary: str | None = None


class OHLCVPoint(BaseModel):
    date: str
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    volume: float | None


class IndicatorSeries(BaseModel):
    name: str
    values: list[dict[str, Any]]  # [{date, value}]


class ScreenerCondition(BaseModel):
    fundamental: dict[str, Any] | None = None
    technical: dict[str, Any] | None = None


class ScreenerRequest(BaseModel):
    market: str = Field("ALL", description="TW / US / ALL")
    symbols: list[str] | None = None  # 若指定則覆蓋 market
    conditions: ScreenerCondition = ScreenerCondition()
    limit: int = 100


class TransactionRequest(BaseModel):
    symbol: str
    side: str = Field(..., description="BUY or SELL")
    qty: float = Field(..., gt=0)
    price: float | None = Field(None, description="未填則以最近收盤價成交")
    note: str | None = None


class PortfolioResetRequest(BaseModel):
    initial_cash: float = 1_000_000.0


class CashFlowRequest(BaseModel):
    amount: float = Field(..., gt=0)
    note: str | None = None


class BacktestRequest(BaseModel):
    symbol: str
    strategy: str
    params: dict[str, Any] | None = None
    start: str | None = None
    end: str | None = None
    init_cash: float = 100_000
    fees: float = 0.001425
    slippage: float = 0.0005


class MultiBacktestRequest(BaseModel):
    symbols: list[str]
    strategy: str
    params: dict[str, Any] | None = None
    start: str | None = None
    end: str | None = None
    init_cash: float = 100_000
    fees: float = 0.001425
    slippage: float = 0.0005
