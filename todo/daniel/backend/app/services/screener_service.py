"""選股服務：給定股票池 + 條件，回傳符合條件的清單。

條件用 dict 結構，例如：
{
    "fundamental": {"pe_max": 20, "dividend_yield_min": 0.03},
    "technical": {"price_above_sma": 60, "rsi_max": 70}
}
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.analytics import indicators
from app.data import fetcher

logger = logging.getLogger(__name__)


def _check_fundamental(info: dict, cond: dict) -> bool:
    if not cond:
        return True
    if "pe_min" in cond and (info.get("pe") is None or info["pe"] < cond["pe_min"]):
        return False
    if "pe_max" in cond and (info.get("pe") is None or info["pe"] > cond["pe_max"]):
        return False
    if "pb_max" in cond and (info.get("pb") is None or info["pb"] > cond["pb_max"]):
        return False
    if "dividend_yield_min" in cond:
        dy = info.get("dividend_yield") or 0
        if dy < cond["dividend_yield_min"]:
            return False
    if "market_cap_min" in cond:
        mc = info.get("market_cap") or 0
        if mc < cond["market_cap_min"]:
            return False
    return True


def _check_technical(symbol: str, cond: dict) -> tuple[bool, dict]:
    if not cond:
        return True, {}
    df = fetcher.get_ohlcv(symbol, period="1y")
    if df is None or df.empty or len(df) < 60:
        return False, {}
    enriched = indicators.enrich(df)
    last = enriched.iloc[-1]

    snapshot = {
        "close": float(last["close"]),
        "sma_20": float(last.get("sma_20")) if last.get("sma_20") == last.get("sma_20") else None,
        "sma_60": float(last.get("sma_60")) if last.get("sma_60") == last.get("sma_60") else None,
        "rsi_14": float(last.get("rsi_14")) if last.get("rsi_14") == last.get("rsi_14") else None,
    }

    if "price_above_sma" in cond:
        n = cond["price_above_sma"]
        col = f"sma_{n}"
        if col not in enriched.columns:
            return False, snapshot
        v = last.get(col)
        if v is None or last["close"] <= v:
            return False, snapshot

    if "price_below_sma" in cond:
        n = cond["price_below_sma"]
        col = f"sma_{n}"
        v = last.get(col)
        if v is None or last["close"] >= v:
            return False, snapshot

    if "rsi_max" in cond:
        v = last.get("rsi_14")
        if v is None or v > cond["rsi_max"]:
            return False, snapshot
    if "rsi_min" in cond:
        v = last.get("rsi_14")
        if v is None or v < cond["rsi_min"]:
            return False, snapshot

    if "macd_bullish" in cond and cond["macd_bullish"]:
        if last.get("macd") is None or last.get("macd_signal") is None:
            return False, snapshot
        if last["macd"] <= last["macd_signal"]:
            return False, snapshot

    return True, snapshot


def _evaluate(symbol: str, conditions: dict) -> dict | None:
    try:
        info = fetcher.get_info(symbol)
        if not _check_fundamental(info, conditions.get("fundamental") or {}):
            return None
        ok, snap = _check_technical(symbol, conditions.get("technical") or {})
        if not ok:
            return None
        return {
            "symbol": symbol,
            "name": info.get("name"),
            "market": info.get("market"),
            "sector": info.get("sector"),
            "pe": info.get("pe"),
            "pb": info.get("pb"),
            "dividend_yield": info.get("dividend_yield"),
            "market_cap": info.get("market_cap"),
            "snapshot": snap,
        }
    except Exception as e:
        logger.warning("screener eval failed for %s: %s", symbol, e)
        return None


def run(symbols: list[str], conditions: dict, max_workers: int = 6, limit: int = 100) -> list[dict]:
    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_evaluate, s, conditions): s for s in symbols}
        for fut in as_completed(futures):
            r = fut.result()
            if r:
                results.append(r)
                if len(results) >= limit:
                    break
    return results
