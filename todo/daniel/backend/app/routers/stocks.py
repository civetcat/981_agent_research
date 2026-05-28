from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.analytics import indicators
from app.data import fetcher
from app.services import llm_service

router = APIRouter()


class AskRequest(BaseModel):
    question: str
    history: list[dict] | None = None


@router.post("/{symbol}/ask")
def ask_stock(symbol: str, req: AskRequest) -> dict:
    """個股 AI 問答：用 Grok 回答關於這檔的問題。每次都會打 LLM，前端要先警告 token 消耗。"""
    sym = fetcher.normalize_symbol(symbol)
    info = fetcher.get_info(sym) or {}
    result = llm_service.ask_about_stock(sym, req.question.strip(), info, req.history)
    result["symbol"] = sym
    return result


def _df_to_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    out = []
    for idx, row in df.iterrows():
        rec: dict[str, Any] = {"date": idx.strftime("%Y-%m-%d")}
        for c in df.columns:
            v = row[c]
            if isinstance(v, (np.floating, float)):
                f = float(v)
                rec[c] = None if math.isnan(f) or math.isinf(f) else round(f, 6)
            elif isinstance(v, (np.integer, int)):
                rec[c] = int(v)
            else:
                rec[c] = v
        out.append(rec)
    return out


@router.get("/search")
def search_stocks(q: str = Query(..., min_length=1), limit: int = 10) -> list[dict]:
    return fetcher.search(q, limit=limit)


@router.get("/{symbol}")
def get_stock(symbol: str) -> dict:
    info = fetcher.get_info(symbol)
    if not info or not info.get("symbol"):
        raise HTTPException(status_code=404, detail="symbol not found")
    return info


@router.get("/{symbol}/ohlcv")
def get_ohlcv(
    symbol: str,
    period: str = Query("1y", description="1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, max"),
) -> dict:
    df = fetcher.get_ohlcv(symbol, period=period)
    if df is None or df.empty:
        raise HTTPException(status_code=404, detail="no data")
    return {"symbol": symbol, "data": _df_to_records(df)}


@router.get("/{symbol}/indicators")
def get_indicators(
    symbol: str,
    period: str = Query("1y"),
    types: str = Query("sma_5,sma_20,sma_60,rsi_14,macd,bb"),
) -> dict:
    df = fetcher.get_ohlcv(symbol, period=period)
    if df is None or df.empty:
        raise HTTPException(status_code=404, detail="no data")
    enriched = indicators.enrich(df)

    name_map = {
        "sma_5": ["sma_5"],
        "sma_20": ["sma_20"],
        "sma_60": ["sma_60"],
        "sma_240": ["sma_240"],
        "ema_12": ["ema_12"],
        "ema_26": ["ema_26"],
        "rsi_14": ["rsi_14"],
        "macd": ["macd", "macd_signal", "macd_hist"],
        "kd": ["k", "d"],
        "bb": ["bb_upper", "bb_middle", "bb_lower"],
    }

    requested = []
    for t in types.split(","):
        t = t.strip()
        if t in name_map:
            requested.extend(name_map[t])

    base = ["open", "high", "low", "close", "volume"]
    cols = [c for c in base if c in enriched.columns] + [
        c for c in requested if c in enriched.columns and c not in base
    ]
    sub = enriched[cols]
    return {"symbol": symbol, "data": _df_to_records(sub)}


@router.get("/{symbol}/fundamentals")
def get_fundamentals(symbol: str) -> dict:
    return fetcher.get_fundamentals(symbol)
