"""ETF 排行：抓 ETF 專屬指標（AUM / 費用率 / 殖利率 / 多期報酬 / TW 法人淨流向）。

設計：
- 用策劃清單，不爬全市場（太雜訊）。
- yfinance 每支 .info 慢且偶爾失敗，做 ThreadPool 並行 + 1 小時 in-memory cache。
- TW ETF 額外加近 5 / 20 日三大法人淨流向（重用 fund_flow.get_tw_institutional）。
- 報酬率從快取的 OHLCV 算，不打外部 API。
"""
from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import pandas as pd
import yfinance as yf

from app.data import etf_list, fetcher, fund_flow

logger = logging.getLogger(__name__)

_CACHE: dict[str, Any] = {}
_CACHE_TS: dict[str, float] = {}
_CACHE_TTL = 60 * 60  # 1 小時


def _cache_get(key: str):
    if key in _CACHE and (time.time() - _CACHE_TS.get(key, 0)) < _CACHE_TTL:
        return _CACHE[key]
    return None


def _cache_set(key: str, value):
    _CACHE[key] = value
    _CACHE_TS[key] = time.time()


def _safe_float(v) -> float | None:
    try:
        if v is None:
            return None
        f = float(v)
        if f != f or f in (float("inf"), float("-inf")):
            return None
        return f
    except (TypeError, ValueError):
        return None


def _period_return_pct(df: pd.DataFrame, days: int) -> float | None:
    if df is None or df.empty or len(df) < days + 1:
        return None
    last = df["close"].iloc[-1]
    prev = df["close"].iloc[-(days + 1)]
    if prev == 0 or pd.isna(prev) or pd.isna(last):
        return None
    return round((last / prev - 1) * 100, 2)


def _fetch_yf_info(symbol: str) -> dict:
    """yfinance .info 對 ETF 提供的欄位較少且不穩定，盡量挑通用欄位。"""
    try:
        info = yf.Ticker(symbol).info or {}
    except Exception as e:
        logger.debug("yfinance info failed %s: %s", symbol, e)
        return {}
    return info


def _tw_inst_net_flow(symbol: str, days_back: int = 30) -> tuple[float | None, float | None]:
    """回傳 (近 5 日合計淨買, 近 20 日合計淨買)。三大法人合計，單位：股。

    若沒資料就回 (None, None)。
    """
    try:
        rows = fund_flow.get_tw_institutional(symbol, days=days_back)
    except Exception as e:
        logger.debug("tw inst flow failed %s: %s", symbol, e)
        return None, None
    if not rows:
        return None, None

    def _sum_recent(n: int) -> float | None:
        recent = rows[-n:] if len(rows) >= n else rows
        if not recent:
            return None
        total = 0.0
        for r in recent:
            for k in ("foreign_net", "trust_net", "dealer_net"):
                v = r.get(k)
                if v is not None:
                    total += float(v)
        return total

    return _sum_recent(5), _sum_recent(20)


def _fetch_one(symbol: str, name: str, category: str, market: str) -> dict | None:
    cache_key = f"etf:{symbol}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    df = fetcher.get_ohlcv(symbol, period="2y")
    if df is None or df.empty:
        return None
    info = _fetch_yf_info(symbol)

    last_close = float(df["close"].iloc[-1])

    record: dict[str, Any] = {
        "symbol": symbol,
        "name": name,
        "category": category,
        "market": market,
        "last_close": round(last_close, 4),
        "currency": info.get("currency"),
        "aum": _safe_float(info.get("totalAssets")),
        "expense_ratio": _safe_float(
            info.get("netExpenseRatio")
            or info.get("annualReportExpenseRatio")
            or info.get("expenseRatio")
        ),
        "dividend_yield": _safe_float(
            info.get("yield") or info.get("trailingAnnualDividendYield")
        ),
        "fund_family": info.get("fundFamily"),
        "return_1m": _period_return_pct(df, 21),
        "return_3m": _period_return_pct(df, 63),
        "return_6m": _period_return_pct(df, 126),
        "return_1y": _period_return_pct(df, 252),
    }

    # yfinance 對殖利率/費用率返回的單位實測都是 already-in-percent
    # (VOO ER 0.03 -> 0.03%, SCHD yield 3.29 -> 3.29%)。所以不乘 100。
    # 但偶爾 yield 會回成小數 (0.0034)，加一個保險：> 0.01 視為已是 %、< 0.01 視為小數。
    dy = record.get("dividend_yield")
    if dy is not None:
        if 0 < dy < 0.5:
            record["dividend_yield"] = round(dy * 100, 2)
        else:
            record["dividend_yield"] = round(dy, 2)

    er = record.get("expense_ratio")
    if er is not None:
        # 同上：< 0.005 視為小數形 (0.0003)，否則視為已是 %
        if 0 < er < 0.005:
            record["expense_ratio"] = round(er * 100, 3)
        else:
            record["expense_ratio"] = round(er, 3)

    if market == "TW":
        net5, net20 = _tw_inst_net_flow(symbol)
        record["inst_net_5d"] = net5
        record["inst_net_20d"] = net20
    else:
        record["inst_net_5d"] = None
        record["inst_net_20d"] = None

    _cache_set(cache_key, record)
    return record


def list_etfs(market: str | None = None, category: str | None = None) -> list[dict]:
    items = etf_list.all_etfs()
    if market:
        items = [x for x in items if x[3] == market.upper()]
    if category:
        items = [x for x in items if x[2] == category]

    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {
            ex.submit(_fetch_one, sym, name, cat, mkt): sym
            for sym, name, cat, mkt in items
        }
        for fut in as_completed(futures):
            try:
                r = fut.result()
            except Exception as e:
                logger.warning("etf fetch error %s: %s", futures[fut], e)
                continue
            if r is not None:
                results.append(r)

    return results


def categories() -> list[dict]:
    return [{"key": k, "label": v} for k, v in etf_list.CATEGORIES]
