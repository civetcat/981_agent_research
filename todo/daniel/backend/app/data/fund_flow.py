"""資金流向資料抓取與技術指標。

- 台股：三大法人買賣超（TWSE T86 RWD 端點，逐日抓 + 本地快取）
- 美股：yfinance Ticker.insider_transactions / institutional_holders
- 共通：MFI / OBV / 成交量 z-score（用 OHLCV 計算）

設計重點：
- TWSE 官方 openapi.twse.com.tw/v1/fund/T86 只回當日資料，
  歷史要用 www.twse.com.tw/rwd/zh/fund/T86?date=YYYYMMDD。
- 為了不每次都打 TWSE，把每個交易日結果存成 JSON 在 data_cache/twse_t86/。
- 個股 symbol 自動分流：detect_market() 決定資料源。
"""
from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import httpx
import yfinance as yf
from ta.volume import MFIIndicator, OnBalanceVolumeIndicator

from app.config import settings
from app.data import fetcher

logger = logging.getLogger(__name__)

TWSE_T86_URL = "https://www.twse.com.tw/rwd/zh/fund/T86"

# RWD 回傳欄位名稱（含括號附註）會偶爾微調，這裡做模糊比對
_FOREIGN_KEYS = ("外陸資買賣超股數(不含外資自營商)", "外資買賣超股數")
_FOREIGN_DEALER_KEYS = ("外資自營商買賣超股數",)
_TRUST_KEYS = ("投信買賣超股數",)
_DEALER_NET_KEYS = ("自營商買賣超股數",)


def _cache_dir() -> Path:
    p = settings.cache_path / "twse_t86"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _stock_code(symbol: str) -> str:
    """2330.TW -> 2330"""
    s = symbol.upper().strip()
    if s.endswith(".TWO"):
        return s[:-4]
    if s.endswith(".TW"):
        return s[:-3]
    return s


def _normalize_key(k: str) -> str:
    """去掉全/半形括號與空白，方便做模糊比對。"""
    out = k
    for ch in (" ", "　", "(", ")", "（", "）"):
        out = out.replace(ch, "")
    return out


def _find_value(row_map: dict[str, str], candidates: tuple[str, ...]) -> int | None:
    # 先直接比對；不中再用正規化後的 key 比對
    for k in candidates:
        if k in row_map:
            return _parse_int(row_map[k])
    norm = {_normalize_key(k): v for k, v in row_map.items()}
    for k in candidates:
        nk = _normalize_key(k)
        if nk in norm:
            return _parse_int(norm[nk])
    return None


def _parse_int(v: Any) -> int | None:
    if v is None:
        return None
    s = str(v).replace(",", "").strip()
    if not s or s in {"--", "-"}:
        return None
    try:
        return int(float(s))
    except ValueError:
        return None


def _fetch_twse_t86_day(d: date) -> list[dict] | None:
    """抓單日 T86 個股資料，回傳已正規化的 list[{code, name, foreign, trust, dealer, net}]。
    遇到非交易日或暫時失敗回 None。成功（即使該日無資料）回空 list 並寫入快取。"""
    date_str = d.strftime("%Y%m%d")
    cache_file = _cache_dir() / f"{date_str}.json"

    if cache_file.exists():
        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            return data
        except Exception:
            pass  # 損毀就重抓

    try:
        r = httpx.get(
            TWSE_T86_URL,
            params={"date": date_str, "selectType": "ALL", "response": "json"},
            timeout=15.0,
            headers={"User-Agent": "Mozilla/5.0 stock-simulator/1.0"},
        )
        r.raise_for_status()
        payload = r.json()
    except Exception as e:
        logger.warning("twse T86 fetch failed for %s: %s", date_str, e)
        return None

    if payload.get("stat") != "OK":
        # 非交易日 TWSE 回 "很抱歉，沒有符合條件的資料!"，當作該日無資料快取空 list
        empty: list[dict] = []
        cache_file.write_text(json.dumps(empty), encoding="utf-8")
        return empty

    fields: list[str] = payload.get("fields", [])
    rows: list[list[str]] = payload.get("data", [])
    result: list[dict] = []
    for row in rows:
        row_map = dict(zip(fields, row))
        code = (row_map.get("證券代號") or row_map.get("Code") or "").strip()
        name = (row_map.get("證券名稱") or row_map.get("Name") or "").strip()
        if not code:
            continue
        foreign = _find_value(row_map, _FOREIGN_KEYS)
        foreign_dealer = _find_value(row_map, _FOREIGN_DEALER_KEYS) or 0
        trust = _find_value(row_map, _TRUST_KEYS)
        dealer = _find_value(row_map, _DEALER_NET_KEYS)
        # 外資合計 = 外陸資 + 外資自營商
        foreign_total = (foreign or 0) + (foreign_dealer or 0)
        net = (foreign_total or 0) + (trust or 0) + (dealer or 0)
        result.append(
            {
                "code": code,
                "name": name,
                "foreign": foreign_total,
                "trust": trust or 0,
                "dealer": dealer or 0,
                "net": net,
            }
        )

    cache_file.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    return result


def get_tw_institutional(symbol: str, days: int = 30) -> list[dict]:
    """抓最近 N 個交易日的三大法人買賣超（張，1 張 = 1000 股）。

    回傳由舊到新：[{date, foreign, trust, dealer, net}, ...]
    """
    code = _stock_code(symbol)
    out: list[dict] = []
    today = date.today()
    # 多抓一些天以涵蓋非交易日，最多回看 90 個日曆日
    seen_days = 0
    max_calendar = 90
    cursor = today
    while len(out) < days and seen_days < max_calendar:
        if cursor.weekday() < 5:  # 週一到週五
            day_rows = _fetch_twse_t86_day(cursor)
            if day_rows is not None:
                for r in day_rows:
                    if r["code"] == code:
                        out.append(
                            {
                                "date": cursor.strftime("%Y-%m-%d"),
                                "foreign": round((r["foreign"] or 0) / 1000, 1),
                                "trust": round((r["trust"] or 0) / 1000, 1),
                                "dealer": round((r["dealer"] or 0) / 1000, 1),
                                "net": round((r["net"] or 0) / 1000, 1),
                            }
                        )
                        break
        cursor -= timedelta(days=1)
        seen_days += 1

    out.reverse()
    return out


def get_us_insider(symbol: str, limit: int = 20) -> list[dict]:
    """yfinance Ticker.insider_transactions"""
    try:
        t = yf.Ticker(symbol)
        df = t.insider_transactions
    except Exception as e:
        logger.warning("insider_transactions failed for %s: %s", symbol, e)
        return []

    if df is None or df.empty:
        return []

    df = df.head(limit).copy()

    def _g(row: pd.Series, *keys: str) -> Any:
        for k in keys:
            if k in row and pd.notna(row[k]):
                return row[k]
        return None

    out: list[dict] = []
    for _, row in df.iterrows():
        d = _g(row, "Start Date", "Date")
        date_str = pd.to_datetime(d).strftime("%Y-%m-%d") if d is not None else None
        out.append(
            {
                "date": date_str,
                "insider": _g(row, "Insider"),
                "position": _g(row, "Position"),
                "transaction": _g(row, "Transaction", "Text"),
                "shares": _to_num(_g(row, "Shares")),
                "value": _to_num(_g(row, "Value")),
            }
        )
    return out


def get_us_institutional(symbol: str) -> list[dict]:
    """yfinance Ticker.institutional_holders → top holders"""
    try:
        t = yf.Ticker(symbol)
        df = t.institutional_holders
    except Exception as e:
        logger.warning("institutional_holders failed for %s: %s", symbol, e)
        return []

    if df is None or df.empty:
        return []

    out: list[dict] = []
    for _, row in df.iterrows():
        out.append(
            {
                "holder": row.get("Holder"),
                "shares": _to_num(row.get("Shares")),
                "value": _to_num(row.get("Value")),
                "pct_held": _to_num(row.get("pctHeld") or row.get("% Out")),
                "date_reported": _fmt_date(row.get("Date Reported")),
            }
        )
    return out


def _to_num(v: Any) -> float | int | None:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return None
    try:
        f = float(v)
        if np.isnan(f) or np.isinf(f):
            return None
        if f.is_integer():
            return int(f)
        return round(f, 6)
    except (ValueError, TypeError):
        return None


def _fmt_date(v: Any) -> str | None:
    if v is None:
        return None
    try:
        return pd.to_datetime(v).strftime("%Y-%m-%d")
    except Exception:
        return None


def compute_money_flow_indicators(symbol: str, days: int = 60) -> list[dict]:
    """用 OHLCV 算 MFI(14) / OBV / 量能 z-score（vs 20 日均量），回最近 days 日序列。"""
    df = fetcher.get_ohlcv(symbol, period="6mo")
    if df is None or df.empty:
        return []

    high = df["high"]
    low = df["low"]
    close = df["close"]
    volume = df["volume"]

    mfi = MFIIndicator(high=high, low=low, close=close, volume=volume, window=14).money_flow_index()
    obv = OnBalanceVolumeIndicator(close=close, volume=volume).on_balance_volume()
    vol_ma20 = volume.rolling(window=20, min_periods=5).mean()
    vol_std20 = volume.rolling(window=20, min_periods=5).std()
    vol_z = (volume - vol_ma20) / vol_std20

    out = pd.DataFrame(
        {
            "close": close,
            "volume": volume,
            "mfi": mfi,
            "obv": obv,
            "vol_ma20": vol_ma20,
            "vol_z": vol_z,
        }
    )
    out = out.replace([np.inf, -np.inf], np.nan).tail(days)

    records: list[dict] = []
    for idx, row in out.iterrows():
        rec = {"date": pd.Timestamp(idx).strftime("%Y-%m-%d")}
        for c in out.columns:
            v = row[c]
            if pd.isna(v):
                rec[c] = None
            elif c in ("volume", "obv"):
                rec[c] = int(v)
            else:
                rec[c] = round(float(v), 4)
        records.append(rec)
    return records


def get_fund_flow(symbol: str) -> dict:
    """整合：依市場回傳對應資金流向資料 + 技術指標。

    各區塊獨立 try/except——yfinance / TWSE 任一個偶爾掛掉，其他資料仍可顯示，
    不會整個 500 回給前端。
    """
    symbol = fetcher.normalize_symbol(symbol)
    market = fetcher.detect_market(symbol)
    payload: dict[str, Any] = {
        "symbol": symbol,
        "market": market,
        "indicators": [],
        "warnings": [],
    }

    try:
        payload["indicators"] = compute_money_flow_indicators(symbol)
    except Exception as e:
        logger.warning("compute_money_flow_indicators failed for %s: %s", symbol, e)
        payload["warnings"].append(f"技術指標計算失敗：{type(e).__name__}")

    if market == "TW":
        try:
            payload["tw_institutional"] = get_tw_institutional(symbol, days=30)
        except Exception as e:
            logger.warning("get_tw_institutional failed for %s: %s", symbol, e)
            payload["tw_institutional"] = []
            payload["warnings"].append(f"三大法人資料載入失敗：{type(e).__name__}")
    else:
        try:
            payload["us_insider"] = get_us_insider(symbol, limit=20)
        except Exception as e:
            logger.warning("get_us_insider failed for %s: %s", symbol, e)
            payload["us_insider"] = []
            payload["warnings"].append(f"Insider 交易資料載入失敗：{type(e).__name__}")
        try:
            payload["us_institutional"] = get_us_institutional(symbol)
        except Exception as e:
            logger.warning("get_us_institutional failed for %s: %s", symbol, e)
            payload["us_institutional"] = []
            payload["warnings"].append(f"機構持股資料載入失敗：{type(e).__name__}")
    return payload
