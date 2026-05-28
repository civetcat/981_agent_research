"""FinMind v4 API 直打（用 httpx，避開 FinMind library 對 ta 的版本鎖定）。

只取台股最有用、yfinance 拿不到的兩種資料：
  1. 月營收 (TaiwanStockMonthRevenue) — 含 YoY、MoM
  2. 歷史股利 (TaiwanStockDividend) — 現金 + 股票股利
其他 (財報、PE 歷史) 後續有需要再加。

設計：
- 一律檢查 token，沒設就回空 {} (上層自己處理「無資料」狀態)
- 結果有檔案快取，每天最多打一次（資料月頻/季頻變化）
- 失敗一律吞掉 + log，不要因為 FinMind 掛掉就讓整個 fundamentals 端點 500
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

API = "https://api.finmindtrade.com/api/v4/data"
_TIMEOUT = 15.0
_CACHE_TTL_SEC = 24 * 3600  # 月營收與股利每天最多打一次


def _stock_id(symbol: str) -> str:
    s = symbol.upper().strip()
    for suf in (".TW", ".TWO"):
        if s.endswith(suf):
            return s[: -len(suf)]
    return s


def _cache_dir() -> Path:
    p = settings.cache_path / "finmind"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _cache_path(dataset: str, stock_id: str) -> Path:
    return _cache_dir() / f"{dataset}_{stock_id}.json"


def _read_cache(dataset: str, stock_id: str):
    p = _cache_path(dataset, stock_id)
    if not p.exists():
        return None
    try:
        if (time.time() - p.stat().st_mtime) > _CACHE_TTL_SEC:
            return None
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_cache(dataset: str, stock_id: str, data) -> None:
    try:
        _cache_path(dataset, stock_id).write_text(
            json.dumps(data, ensure_ascii=False), encoding="utf-8"
        )
    except Exception as e:
        logger.debug("finmind cache write failed: %s", e)


def _fetch(dataset: str, stock_id: str, start_date: str) -> list[dict]:
    token = settings.finmind_token.strip()
    if not token:
        return []

    cached = _read_cache(dataset, stock_id)
    if cached is not None:
        return cached

    params = {
        "dataset": dataset,
        "data_id": stock_id,
        "start_date": start_date,
        "token": token,
    }
    try:
        with httpx.Client(timeout=_TIMEOUT) as c:
            r = c.get(API, params=params)
            r.raise_for_status()
            payload = r.json()
    except Exception as e:
        logger.warning("finmind %s/%s failed: %s", dataset, stock_id, e)
        return []

    if payload.get("status") != 200:
        logger.warning("finmind %s/%s api error: %s", dataset, stock_id, payload.get("msg"))
        return []

    rows = payload.get("data") or []
    _write_cache(dataset, stock_id, rows)
    return rows


def get_monthly_revenue(symbol: str, years: int = 3) -> list[dict]:
    """月營收 (含 YoY)。回傳近 N 年資料，新到舊排序由 FinMind 給定。
    欄位：date, revenue, revenue_year, revenue_month, revenue_yoy 等。"""
    stock_id = _stock_id(symbol)
    today = time.gmtime()
    start = f"{today.tm_year - years}-01-01"
    rows = _fetch("TaiwanStockMonthRevenue", stock_id, start)
    if not rows:
        return []

    # 統一欄位 + 按日期升序
    out: list[dict] = []
    for r in rows:
        out.append(
            {
                "date": r.get("date"),
                "year": r.get("revenue_year"),
                "month": r.get("revenue_month"),
                "revenue": r.get("revenue"),
                "yoy_pct": None,
                "mom_pct": None,
            }
        )
    out.sort(key=lambda x: x.get("date") or "")

    # FinMind 不一定提供上期欄位，自己計算 YoY (對 12 期前) 與 MoM (對 1 期前)
    for i, cur in enumerate(out):
        rev = cur.get("revenue")
        if not rev:
            continue
        if i >= 1:
            prev = out[i - 1].get("revenue")
            if prev:
                cur["mom_pct"] = round((rev / prev - 1) * 100, 2)
        if i >= 12:
            prev_yr = out[i - 12].get("revenue")
            if prev_yr:
                cur["yoy_pct"] = round((rev / prev_yr - 1) * 100, 2)

    return out


def get_dividend(symbol: str, years: int = 10) -> list[dict]:
    """歷史股利。FinMind 欄位：date(除息日), CashEarningsDistribution, StockEarningsDistribution 等。"""
    stock_id = _stock_id(symbol)
    today = time.gmtime()
    start = f"{today.tm_year - years}-01-01"
    rows = _fetch("TaiwanStockDividend", stock_id, start)
    if not rows:
        return []
    out = []
    for r in rows:
        cash = (
            (r.get("CashEarningsDistribution") or 0)
            + (r.get("CashStatutorySurplus") or 0)
            + (r.get("CashExDividendTradingDate") and 0 or 0)  # noop, kept for clarity
        )
        stock_div = (
            (r.get("StockEarningsDistribution") or 0)
            + (r.get("StockStatutorySurplus") or 0)
        )
        out.append(
            {
                "date": r.get("date") or r.get("CashDividendPaymentDate"),
                "cash_dividend": round(float(cash), 4) if cash else None,
                "stock_dividend": round(float(stock_div), 4) if stock_div else None,
                "year": (r.get("date") or "")[:4],
            }
        )
    out.sort(key=lambda x: x.get("date") or "")
    # 同年合併（同一年可能有多次配發）
    merged: dict[str, dict] = {}
    for r in out:
        y = r.get("year")
        if not y:
            continue
        if y not in merged:
            merged[y] = {"year": y, "cash_dividend": 0.0, "stock_dividend": 0.0}
        merged[y]["cash_dividend"] = round(
            (merged[y]["cash_dividend"] or 0) + (r.get("cash_dividend") or 0), 4
        )
        merged[y]["stock_dividend"] = round(
            (merged[y]["stock_dividend"] or 0) + (r.get("stock_dividend") or 0), 4
        )
    return sorted(merged.values(), key=lambda x: x["year"])
