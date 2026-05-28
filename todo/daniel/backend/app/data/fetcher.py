"""資料抓取：統一 symbol 格式（台股 2330.TW、美股 AAPL）。

策略：
- OHLCV 日線：一律先用 yfinance（覆蓋台股美股）
- 台股財報 / 籌碼：FinMind（如果有 token）
- 美股財報：yfinance 內建 .info / .financials
"""
from __future__ import annotations

import logging
from typing import Literal

import pandas as pd
import yfinance as yf

from app.data import store

logger = logging.getLogger(__name__)

Market = Literal["TW", "US"]


def detect_market(symbol: str) -> Market:
    s = symbol.upper()
    if s.endswith(".TW") or s.endswith(".TWO"):
        return "TW"
    return "US"


def normalize_symbol(symbol: str) -> str:
    """台股純數字 (2330) 自動補 .TW，美股保持原樣。"""
    s = symbol.strip().upper()
    if s.isdigit() and len(s) == 4:
        return f"{s}.TW"
    return s


_PERIOD_DAYS = {
    "1mo": 31,
    "3mo": 92,
    "6mo": 183,
    "1y": 366,
    "2y": 731,
    "5y": 1826,
    "10y": 3653,
    "max": None,
}


def _slice_by_period(df: pd.DataFrame, period: str) -> pd.DataFrame:
    days = _PERIOD_DAYS.get(period)
    if days is None or df.empty:
        return df
    cutoff = df.index.max() - pd.Timedelta(days=days)
    return df[df.index >= cutoff]


def _fetch_full(symbol: str) -> pd.DataFrame:
    """一律抓 max 期間並寫快取，呼叫端再切片。"""
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="max", auto_adjust=False)
    except Exception as e:
        logger.error("yfinance fetch failed for %s: %s", symbol, e)
        cached = store.load(symbol)
        if cached is not None:
            return cached
        raise

    if hist is None or hist.empty:
        cached = store.load(symbol)
        if cached is not None:
            return cached
        return pd.DataFrame()

    df = hist.rename(
        columns={
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Adj Close": "adj_close",
            "Volume": "volume",
        }
    )
    df.index.name = "date"
    keep = ["open", "high", "low", "close", "adj_close", "volume"]
    df = df[[c for c in keep if c in df.columns]]
    df = df.dropna(subset=["close"])
    store.save(symbol, df)
    return df


def get_ohlcv(
    symbol: str,
    period: str = "5y",
    use_cache: bool = True,
) -> pd.DataFrame:
    """回傳欄位：date(index), open, high, low, close, volume, adj_close。
    內部一律抓 / 快取 max 期間，period 只決定回傳時切多少。"""
    symbol = normalize_symbol(symbol)

    if use_cache and store.is_fresh(symbol):
        cached = store.load(symbol)
        if cached is not None and not cached.empty:
            return _slice_by_period(cached, period)

    df = _fetch_full(symbol)
    return _slice_by_period(df, period)


def get_info(symbol: str) -> dict:
    """個股基本資料（名稱、產業、市值等）。"""
    symbol = normalize_symbol(symbol)
    try:
        info = yf.Ticker(symbol).info or {}
    except Exception as e:
        logger.warning("info fetch failed for %s: %s", symbol, e)
        return {"symbol": symbol}

    return {
        "symbol": symbol,
        "name": info.get("longName") or info.get("shortName") or symbol,
        "market": detect_market(symbol),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "currency": info.get("currency"),
        "exchange": info.get("exchange"),
        "market_cap": info.get("marketCap"),
        "pe": info.get("trailingPE"),
        "pb": info.get("priceToBook"),
        "dividend_yield": info.get("dividendYield"),
        "eps": info.get("trailingEps"),
        "summary": info.get("longBusinessSummary"),
    }


def search(query: str, limit: int = 10) -> list[dict]:
    """簡易搜尋：用 yfinance Search API。"""
    q = query.strip()
    if not q:
        return []
    try:
        from yfinance import Search

        res = Search(q, max_results=limit).quotes
    except Exception as e:
        logger.warning("search failed: %s", e)
        return []

    out = []
    for r in res or []:
        sym = r.get("symbol") or ""
        if not sym:
            continue
        out.append(
            {
                "symbol": sym,
                "name": r.get("longname") or r.get("shortname") or sym,
                "exchange": r.get("exchange"),
                "type": r.get("quoteType"),
            }
        )
    return out


def get_fundamentals(symbol: str) -> dict:
    """財報重點。
    - 美股：yfinance .info
    - 台股：yfinance .info + FinMind 月營收 / 歷史股利（有 token 才補）
    """
    symbol = normalize_symbol(symbol)
    info = get_info(symbol)
    market = detect_market(symbol)

    payload = {
        "symbol": symbol,
        "pe": info.get("pe"),
        "pb": info.get("pb"),
        "eps": info.get("eps"),
        "dividend_yield": info.get("dividend_yield"),
        "market_cap": info.get("market_cap"),
        "source": "yfinance",
    }

    if market == "TW":
        try:
            from app.data import finmind
            mr = finmind.get_monthly_revenue(symbol, years=3)
            div = finmind.get_dividend(symbol, years=10)
            if mr or div:
                payload["finmind"] = {
                    "monthly_revenue": mr[-24:],   # 最多 24 個月
                    "dividend": div,
                }
                payload["source"] = "yfinance + finmind"
        except Exception as e:
            logger.warning("finmind enrich failed for %s: %s", symbol, e)

    return payload
