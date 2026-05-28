"""手刻向量化回測引擎：吃 entries/exits 訊號，輸出績效指標 + 權益曲線 + 交易紀錄。

模型假設：
- 全進全出（每次訊號出來就把可用現金全部買入 / 把持倉全部賣出）
- 隔日開盤價成交（避免未來函數）
- 手續費按成交金額比例扣除，滑價以價格折扣形式建模
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from app.backtest import strategies
from app.data import fetcher

TRADING_DAYS = 252


def _safe(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, (np.floating, float)):
        f = float(v)
        if math.isnan(f) or math.isinf(f):
            return None
        return round(f, 6)
    if isinstance(v, (np.integer, int)):
        return int(v)
    if isinstance(v, pd.Timestamp):
        return v.strftime("%Y-%m-%d")
    return v


def _simulate(
    df: pd.DataFrame,
    entries: pd.Series,
    exits: pd.Series,
    init_cash: float,
    fees: float,
    slippage: float,
) -> dict:
    """逐日模擬。訊號於當日收盤後產生，於下一根 K 棒以開盤價執行。"""
    open_p = df["open"].to_numpy()
    close_p = df["close"].to_numpy()
    sig_entry = entries.to_numpy()
    sig_exit = exits.to_numpy()
    n = len(df)

    cash = init_cash
    qty = 0.0
    avg_cost = 0.0

    equity = np.zeros(n)
    position_held = np.zeros(n, dtype=bool)
    trades: list[dict] = []
    open_trade: dict | None = None

    for i in range(n):
        if i > 0:
            ex_signal = sig_exit[i - 1] and qty > 0
            en_signal = sig_entry[i - 1] and qty == 0

            exec_price = open_p[i]
            if not np.isfinite(exec_price):
                exec_price = close_p[i]

            if ex_signal:
                sell_price = exec_price * (1 - slippage)
                proceeds = qty * sell_price * (1 - fees)
                cash += proceeds
                pnl = proceeds - (qty * avg_cost)
                if open_trade is not None:
                    open_trade["exit_date"] = df.index[i]
                    open_trade["exit_price"] = sell_price
                    open_trade["pnl"] = pnl
                    open_trade["return_pct"] = (
                        (sell_price / avg_cost - 1) * 100 if avg_cost > 0 else 0.0
                    )
                    trades.append(open_trade)
                    open_trade = None
                qty = 0.0
                avg_cost = 0.0

            if en_signal and cash > 0:
                buy_price = exec_price * (1 + slippage)
                affordable = cash * (1 - fees)
                buy_qty = affordable / buy_price
                cost = buy_qty * buy_price
                cash -= cost * (1 + fees)
                qty = buy_qty
                avg_cost = buy_price
                open_trade = {
                    "entry_date": df.index[i],
                    "entry_price": buy_price,
                    "size": buy_qty,
                }

        equity[i] = cash + qty * close_p[i]
        position_held[i] = qty > 0

    if qty > 0 and open_trade is not None:
        last_price = close_p[-1]
        open_trade["exit_date"] = None
        open_trade["exit_price"] = None
        open_trade["pnl"] = (last_price - avg_cost) * qty
        open_trade["return_pct"] = (last_price / avg_cost - 1) * 100 if avg_cost > 0 else 0.0
        trades.append(open_trade)

    metrics = _compute_metrics(equity, position_held, trades, init_cash)
    return {
        "equity": equity,
        "trades": trades,
        "metrics": metrics,
    }


def _compute_metrics(
    equity: np.ndarray,
    held: np.ndarray,
    trades: list[dict],
    init_cash: float,
) -> dict:
    n = len(equity)
    if n == 0:
        return {}

    total_return = (equity[-1] / init_cash - 1) * 100
    years = n / TRADING_DAYS
    annual_return = ((equity[-1] / init_cash) ** (1 / years) - 1) * 100 if years > 0 else 0.0

    daily_ret = np.diff(equity) / equity[:-1]
    daily_ret = daily_ret[np.isfinite(daily_ret)]

    if daily_ret.size > 1 and daily_ret.std() > 0:
        sharpe = (daily_ret.mean() / daily_ret.std()) * math.sqrt(TRADING_DAYS)
    else:
        sharpe = 0.0

    downside = daily_ret[daily_ret < 0]
    if downside.size > 1 and downside.std() > 0:
        sortino = (daily_ret.mean() / downside.std()) * math.sqrt(TRADING_DAYS)
    else:
        sortino = 0.0

    running_max = np.maximum.accumulate(equity)
    drawdown = (equity - running_max) / running_max
    max_dd = float(drawdown.min()) * 100 if drawdown.size > 0 else 0.0

    closed = [t for t in trades if t.get("exit_date") is not None]
    wins = [t for t in closed if (t.get("pnl") or 0) > 0]
    win_rate = (len(wins) / len(closed) * 100) if closed else 0.0
    best = max((t["return_pct"] for t in closed), default=0.0)
    worst = min((t["return_pct"] for t in closed), default=0.0)
    exposure = float(held.mean()) * 100 if held.size > 0 else 0.0

    return {
        "total_return": _safe(total_return),
        "annual_return": _safe(annual_return),
        "max_drawdown": _safe(max_dd),
        "sharpe": _safe(sharpe),
        "sortino": _safe(sortino),
        "win_rate": _safe(win_rate),
        "trades": len(closed),
        "best_trade": _safe(best),
        "worst_trade": _safe(worst),
        "exposure": _safe(exposure),
    }


def run(
    symbol: str,
    strategy_key: str,
    params: dict | None = None,
    start: str | None = None,
    end: str | None = None,
    init_cash: float = 100_000,
    fees: float = 0.001425,
    slippage: float = 0.0005,
) -> dict:
    params = params or {}

    df = fetcher.get_ohlcv(symbol, period="max")
    if df is None or df.empty:
        raise ValueError(f"no data for {symbol}")

    if start:
        ts = pd.Timestamp(start)
        if df.index.tz is not None:
            ts = ts.tz_localize(df.index.tz)
        df = df[df.index >= ts]
    if end:
        ts = pd.Timestamp(end)
        if df.index.tz is not None:
            ts = ts.tz_localize(df.index.tz)
        df = df[df.index <= ts]
    if df.empty or len(df) < 2:
        raise ValueError("date range too small")

    meta, fn = strategies.get(strategy_key)
    final_params = {**meta.params, **params}
    entries, exits = fn(df, **final_params)
    entries = entries.reindex(df.index).fillna(False)
    exits = exits.reindex(df.index).fillna(False)

    sim = _simulate(df, entries, exits, init_cash, fees, slippage)

    equity_curve = [
        {"date": idx.strftime("%Y-%m-%d"), "value": _safe(v)}
        for idx, v in zip(df.index, sim["equity"])
    ]
    benchmark = (df["close"] / df["close"].iloc[0]) * init_cash
    benchmark_curve = [
        {"date": idx.strftime("%Y-%m-%d"), "value": _safe(v)}
        for idx, v in benchmark.items()
    ]

    trades_out = []
    for t in sim["trades"]:
        trades_out.append(
            {
                "entry_date": _safe(t.get("entry_date")),
                "exit_date": _safe(t.get("exit_date")),
                "entry_price": _safe(t.get("entry_price")),
                "exit_price": _safe(t.get("exit_price")),
                "size": _safe(t.get("size")),
                "pnl": _safe(t.get("pnl")),
                "return_pct": _safe(t.get("return_pct")),
            }
        )

    return {
        "symbol": symbol,
        "strategy": strategy_key,
        "params": final_params,
        "start": df.index[0].strftime("%Y-%m-%d"),
        "end": df.index[-1].strftime("%Y-%m-%d"),
        "init_cash": init_cash,
        "metrics": sim["metrics"],
        "equity_curve": equity_curve,
        "benchmark_curve": benchmark_curve,
        "trades": trades_out,
    }
