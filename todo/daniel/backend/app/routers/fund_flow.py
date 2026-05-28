"""資金流向 + AI 原因分析 API。"""
from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Query

from app.data import fetcher, fund_flow
from app.services import llm_service

router = APIRouter()

# 簡易 in-memory cache：key=(symbol, YYYY-MM-DD)，避免每次都重打 LLM 燒 token
_ANALYSIS_CACHE: dict[tuple[str, str], dict[str, Any]] = {}
_ANALYSIS_TTL = 24 * 60 * 60  # 24 小時（同一天打過一次就好）


def _today_key() -> str:
    return time.strftime("%Y-%m-%d")


def _get_cached(sym: str) -> dict | None:
    cache_key = (sym, _today_key())
    if cache_key not in _ANALYSIS_CACHE:
        return None
    cached = _ANALYSIS_CACHE[cache_key]
    if time.time() - cached["_ts"] >= _ANALYSIS_TTL:
        return None
    return {k: v for k, v in cached.items() if not k.startswith("_")}


@router.get("/{symbol}")
def get_fund_flow(symbol: str) -> dict:
    """永遠回 200。若所有資料都抓失敗，payload['warnings'] 會說明原因，
    前端 FundFlowSection 會顯示 placeholder。這樣個股頁不會因為 TWSE / yfinance
    偶爾抽風就整塊變紅。"""
    sym = fetcher.normalize_symbol(symbol)
    try:
        return fund_flow.get_fund_flow(sym)
    except Exception as e:
        return {
            "symbol": sym,
            "market": fetcher.detect_market(sym),
            "indicators": [],
            "warnings": [f"資金流向資料整體失敗：{type(e).__name__} - {e}"],
        }


@router.get("/{symbol}/analysis")
def get_analysis(
    symbol: str,
    refresh: bool = Query(False),
    check_only: bool = Query(
        False,
        description="只查快取，不呼叫 LLM。前端開頁時用，避免每次造訪都打 Grok。",
    ),
) -> dict:
    sym = fetcher.normalize_symbol(symbol)

    if not refresh:
        cached = _get_cached(sym)
        if cached is not None:
            return {**cached, "cached": True}

    if check_only:
        return {"cached": False, "symbol": sym}

    flow = fund_flow.get_fund_flow(sym)
    info = fetcher.get_info(sym)
    result = llm_service.analyze_fund_flow(sym, flow, info)
    result["symbol"] = sym

    _ANALYSIS_CACHE[(sym, _today_key())] = {**result, "_ts": time.time()}
    return {**result, "cached": False}
