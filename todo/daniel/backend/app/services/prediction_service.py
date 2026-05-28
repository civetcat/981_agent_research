"""策略預測服務。

「預測」= 用該策略在該股票上的歷史回測統計 + 當前波動度，推算「若現在進場，
歷史上類似情境下的目標價 / 停損價 / 目標區間」。

這不是預言，而是把回測統計外推到當前價格的數學運算：
  - 進場價 entry = 最近收盤
  - 預期目標價 target_high = entry × (1 + avg_win_pct/100)        歷史平均贏單漲幅
  - 預期停損價 target_low  = entry × (1 + avg_loss_pct/100)       歷史平均輸單跌幅 (avg_loss_pct 為負)
  - ATR 區間   atr_band   = ±ATR(14) / entry × 100               近期波動度
  - 期望值     expected_pct = win_rate × avg_win + (1-win_rate) × avg_loss
"""
from __future__ import annotations

import logging
import math

import numpy as np
import pandas as pd

from app.backtest.runner import _simulate
from app.data import fetcher
from app.services.recommend_service import HORIZON_STRATEGY

logger = logging.getLogger(__name__)


def _safe(v) -> float | None:
    if v is None:
        return None
    if isinstance(v, (np.floating, float)):
        f = float(v)
        if math.isnan(f) or math.isinf(f):
            return None
        return round(f, 4)
    if isinstance(v, (np.integer, int)):
        return int(v)
    return v


def _atr(df: pd.DataFrame, window: int = 14) -> float | None:
    if df.empty or len(df) < window + 1:
        return None
    h, l, c = df["high"], df["low"], df["close"]
    prev_c = c.shift(1)
    tr = pd.concat(
        [(h - l).abs(), (h - prev_c).abs(), (l - prev_c).abs()], axis=1
    ).max(axis=1)
    atr = tr.rolling(window=window, min_periods=window).mean()
    last = atr.iloc[-1]
    if pd.isna(last):
        return None
    return float(last)


def project(
    last_close: float,
    avg_win_pct: float,
    avg_loss_pct: float,
    atr_value: float | None,
) -> dict:
    """純數學計算：把已知統計值外推成價位。沒有副作用。"""
    target_high = last_close * (1 + avg_win_pct / 100.0)
    target_low = last_close * (1 + avg_loss_pct / 100.0)
    atr_pct = (atr_value / last_close * 100.0) if atr_value and last_close else None
    rr_ratio = abs(avg_win_pct / avg_loss_pct) if avg_loss_pct else None  # 賠率比

    return {
        "entry": _safe(last_close),
        "target_high": _safe(target_high),
        "target_low": _safe(target_low),
        "upside_pct": _safe(avg_win_pct),
        "downside_pct": _safe(avg_loss_pct),
        "atr": _safe(atr_value),
        "atr_pct": _safe(atr_pct),
        "atr_high": _safe(last_close + (atr_value or 0)),
        "atr_low": _safe(last_close - (atr_value or 0)),
        "risk_reward_ratio": _safe(rr_ratio),
    }


def for_stock(symbol: str) -> dict:
    """對單一股票，跑五個持有期策略並算預測。"""
    symbol = fetcher.normalize_symbol(symbol)
    df = fetcher.get_ohlcv(symbol, period="5y")
    if df is None or df.empty or len(df) < 80:
        return {"symbol": symbol, "predictions": [], "error": "insufficient data"}

    last_close = float(df["close"].iloc[-1])
    atr_val = _atr(df, 14)

    out = []
    for horizon, (strategy_name, signal_fn) in HORIZON_STRATEGY.items():
        try:
            entries, exits = signal_fn(df)
        except Exception as e:
            logger.debug("signal failed %s/%d: %s", symbol, horizon, e)
            continue
        entries = entries.reindex(df.index).fillna(False)
        exits = exits.reindex(df.index).fillna(False)

        sim = _simulate(df, entries, exits, init_cash=100_000, fees=0.001425, slippage=0.0005)
        closed = [t for t in sim["trades"] if t.get("exit_date") is not None]
        if len(closed) < 3:
            out.append(
                {
                    "horizon": horizon,
                    "strategy": strategy_name,
                    "n_trades": len(closed),
                    "warning": "歷史樣本太少（< 3），預測不可信",
                    "entry": _safe(last_close),
                }
            )
            continue

        wins = [t for t in closed if (t.get("return_pct") or 0) > 0]
        losses = [t for t in closed if (t.get("return_pct") or 0) <= 0]
        win_rate = len(wins) / len(closed)
        avg_win = float(np.mean([t["return_pct"] for t in wins])) if wins else 0.0
        avg_loss = float(np.mean([t["return_pct"] for t in losses])) if losses else 0.0
        expected = win_rate * avg_win + (1 - win_rate) * avg_loss

        proj = project(last_close, avg_win, avg_loss, atr_val)

        # 是否目前已有訊號（最近 3 個交易日內）
        recent_entries = entries.iloc[-3:]
        has_signal = bool(recent_entries.any())
        signal_date = (
            recent_entries[recent_entries].index[-1].strftime("%Y-%m-%d")
            if has_signal
            else None
        )

        out.append(
            {
                "horizon": horizon,
                "strategy": strategy_name,
                "n_trades": len(closed),
                "win_rate": _safe(win_rate),
                "avg_win_pct": _safe(avg_win),
                "avg_loss_pct": _safe(avg_loss),
                "expected_return_pct": _safe(expected),
                "has_signal_now": has_signal,
                "signal_date": signal_date,
                **proj,
            }
        )

    return {
        "symbol": symbol,
        "last_close": _safe(last_close),
        "atr": _safe(atr_val),
        "predictions": out,
    }
