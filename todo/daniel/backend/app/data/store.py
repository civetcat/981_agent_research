"""Parquet 快取：每檔股票一個 .parquet 檔，存日線 OHLCV。"""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from app.config import settings


def _path_for(symbol: str) -> Path:
    safe = symbol.replace("/", "_").replace("\\", "_")
    return settings.cache_path / f"{safe}.parquet"


def is_fresh(symbol: str, ttl_hours: int | None = None) -> bool:
    p = _path_for(symbol)
    if not p.exists():
        return False
    ttl = ttl_hours if ttl_hours is not None else settings.cache_ttl_hours
    age = datetime.now() - datetime.fromtimestamp(p.stat().st_mtime)
    return age < timedelta(hours=ttl)


def load(symbol: str) -> pd.DataFrame | None:
    p = _path_for(symbol)
    if not p.exists():
        return None
    try:
        return pd.read_parquet(p)
    except Exception:
        return None


def save(symbol: str, df: pd.DataFrame) -> None:
    if df is None or df.empty:
        return
    p = _path_for(symbol)
    df.to_parquet(p, index=True)
