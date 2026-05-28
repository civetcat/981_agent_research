"""內建回測策略：每個策略接收 close (Series)，回傳 entries / exits 兩個 bool Series。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pandas as pd

from app.analytics import indicators


@dataclass
class StrategyMeta:
    key: str
    name: str
    description: str
    params: dict  # name -> default


def _ma_cross(df: pd.DataFrame, fast: int = 5, slow: int = 20) -> tuple[pd.Series, pd.Series]:
    f = indicators.sma(df["close"], fast)
    s = indicators.sma(df["close"], slow)
    entries = (f > s) & (f.shift(1) <= s.shift(1))
    exits = (f < s) & (f.shift(1) >= s.shift(1))
    return entries.fillna(False), exits.fillna(False)


def _rsi_reversal(df: pd.DataFrame, low: int = 30, high: int = 70, window: int = 14) -> tuple[pd.Series, pd.Series]:
    r = indicators.rsi(df["close"], window)
    entries = (r < low) & (r.shift(1) >= low)
    exits = (r > high) & (r.shift(1) <= high)
    return entries.fillna(False), exits.fillna(False)


def _bbands_breakout(df: pd.DataFrame, window: int = 20, dev: float = 2.0) -> tuple[pd.Series, pd.Series]:
    bb = indicators.bbands(df["close"], window, dev)
    entries = (df["close"] > bb["upper"]) & (df["close"].shift(1) <= bb["upper"].shift(1))
    exits = (df["close"] < bb["middle"]) & (df["close"].shift(1) >= bb["middle"].shift(1))
    return entries.fillna(False), exits.fillna(False)


def _buy_and_hold(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    entries = pd.Series(False, index=df.index)
    exits = pd.Series(False, index=df.index)
    if len(entries) > 0:
        entries.iloc[0] = True
    return entries, exits


REGISTRY: dict[str, tuple[StrategyMeta, Callable]] = {
    "ma_cross": (
        StrategyMeta(
            key="ma_cross",
            name="均線黃金交叉 / 死亡交叉",
            description="快線上穿慢線買進，下穿賣出",
            params={"fast": 5, "slow": 20},
        ),
        _ma_cross,
    ),
    "rsi_reversal": (
        StrategyMeta(
            key="rsi_reversal",
            name="RSI 超買超賣反轉",
            description="RSI 跌破 low 進場，突破 high 出場",
            params={"low": 30, "high": 70, "window": 14},
        ),
        _rsi_reversal,
    ),
    "bbands_breakout": (
        StrategyMeta(
            key="bbands_breakout",
            name="布林通道突破",
            description="收盤突破上軌進場，跌破中軌出場",
            params={"window": 20, "dev": 2.0},
        ),
        _bbands_breakout,
    ),
    "buy_and_hold": (
        StrategyMeta(
            key="buy_and_hold",
            name="買入並持有",
            description="期初買進，全期持有（基準對照組）",
            params={},
        ),
        _buy_and_hold,
    ),
}


def list_strategies() -> list[StrategyMeta]:
    return [m for m, _ in REGISTRY.values()]


def get(key: str) -> tuple[StrategyMeta, Callable]:
    if key not in REGISTRY:
        raise KeyError(f"unknown strategy: {key}")
    return REGISTRY[key]
