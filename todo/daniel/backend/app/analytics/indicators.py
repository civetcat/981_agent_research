"""技術指標：基於 ta 套件。輸入 DataFrame 必須含 open/high/low/close/volume。"""
from __future__ import annotations

import numpy as np
import pandas as pd
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import EMAIndicator, MACD, SMAIndicator
from ta.volatility import BollingerBands


def sma(close: pd.Series, window: int) -> pd.Series:
    return SMAIndicator(close, window=window, fillna=False).sma_indicator()


def ema(close: pd.Series, window: int) -> pd.Series:
    return EMAIndicator(close, window=window, fillna=False).ema_indicator()


def rsi(close: pd.Series, window: int = 14) -> pd.Series:
    return RSIIndicator(close, window=window, fillna=False).rsi()


def macd(close: pd.Series) -> dict[str, pd.Series]:
    m = MACD(close, fillna=False)
    return {
        "macd": m.macd(),
        "signal": m.macd_signal(),
        "hist": m.macd_diff(),
    }


def kd(
    high: pd.Series, low: pd.Series, close: pd.Series, window: int = 9
) -> dict[str, pd.Series]:
    s = StochasticOscillator(high=high, low=low, close=close, window=window, smooth_window=3)
    return {"k": s.stoch(), "d": s.stoch_signal()}


def bbands(close: pd.Series, window: int = 20, dev: float = 2.0) -> dict[str, pd.Series]:
    b = BollingerBands(close, window=window, window_dev=dev, fillna=False)
    return {"upper": b.bollinger_hband(), "middle": b.bollinger_mavg(), "lower": b.bollinger_lband()}


# ---- 高階：把多個指標一次算好附加到 DataFrame ----
def enrich(df: pd.DataFrame) -> pd.DataFrame:
    """在原 df 後面追加常用指標欄位，回傳新 df。"""
    if df.empty:
        return df
    out = df.copy()
    out["sma_5"] = sma(out["close"], 5)
    out["sma_20"] = sma(out["close"], 20)
    out["sma_60"] = sma(out["close"], 60)
    out["sma_240"] = sma(out["close"], 240)
    out["ema_12"] = ema(out["close"], 12)
    out["ema_26"] = ema(out["close"], 26)
    out["rsi_14"] = rsi(out["close"], 14)

    m = macd(out["close"])
    out["macd"] = m["macd"]
    out["macd_signal"] = m["signal"]
    out["macd_hist"] = m["hist"]

    k = kd(out["high"], out["low"], out["close"], 9)
    out["k"] = k["k"]
    out["d"] = k["d"]

    bb = bbands(out["close"])
    out["bb_upper"] = bb["upper"]
    out["bb_middle"] = bb["middle"]
    out["bb_lower"] = bb["lower"]

    out = out.replace([np.inf, -np.inf], np.nan)
    return out
