"""推薦選股 = 訊號偵測 + 歷史回測統計 + 期望值計算。

對每個（持有期，股票）：
1. 用對應策略跑歷史回測 → 取勝率、平均勝幅、平均敗幅、最大回撤
2. 檢查最近 K 個交易日有沒有「新進場訊號」
3. 預期報酬 = win_rate × avg_win + (1 - win_rate) × avg_loss

策略對應（短期到長期）：
  5d  → SMA 5/10 黃金交叉
  10d → SMA 5/20 黃金交叉
  15d → SMA 10/20 黃金交叉
  20d → 布林通道突破
  30d → SMA 20/60 黃金交叉
"""
from __future__ import annotations

import logging
import math
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Callable

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.analytics import indicators
from app.backtest.runner import _simulate
from app.data import fetcher
from app.models import db as orm

logger = logging.getLogger(__name__)


def _ma_cross(df: pd.DataFrame, fast: int, slow: int) -> tuple[pd.Series, pd.Series]:
    f = indicators.sma(df["close"], fast)
    s = indicators.sma(df["close"], slow)
    entries = (f > s) & (f.shift(1) <= s.shift(1))
    exits = (f < s) & (f.shift(1) >= s.shift(1))
    return entries.fillna(False), exits.fillna(False)


def _bbands_breakout(df: pd.DataFrame, window: int = 20, dev: float = 2.0):
    bb = indicators.bbands(df["close"], window, dev)
    entries = (df["close"] > bb["upper"]) & (df["close"].shift(1) <= bb["upper"].shift(1))
    exits = (df["close"] < bb["middle"]) & (df["close"].shift(1) >= bb["middle"].shift(1))
    return entries.fillna(False), exits.fillna(False)


HORIZON_STRATEGY: dict[int, tuple[str, Callable]] = {
    5:  ("SMA 5/10 cross",  lambda df: _ma_cross(df, 5, 10)),
    10: ("SMA 5/20 cross",  lambda df: _ma_cross(df, 5, 20)),
    15: ("SMA 10/20 cross", lambda df: _ma_cross(df, 10, 20)),
    20: ("BBands breakout", lambda df: _bbands_breakout(df, 20, 2.0)),
    30: ("SMA 20/60 cross", lambda df: _ma_cross(df, 20, 60)),
}

# 訊號需出現在最近幾個交易日內才算「現在可進場」
RECENT_WINDOW_DAYS = 3


def _safe_pct(v: float) -> float:
    if v is None or not math.isfinite(v):
        return 0.0
    return round(v, 4)


def _evaluate_one(
    symbol: str, horizon: int, name: str | None, market: str | None
) -> dict | None:
    strategy_name, signal_fn = HORIZON_STRATEGY[horizon]

    try:
        df = fetcher.get_ohlcv(symbol, period="5y")
    except Exception as e:
        logger.debug("fetch failed %s: %s", symbol, e)
        return None
    if df is None or df.empty or len(df) < 80:
        return None

    try:
        entries, exits = signal_fn(df)
    except Exception as e:
        logger.debug("signal failed %s: %s", symbol, e)
        return None

    entries = entries.reindex(df.index).fillna(False)
    exits = exits.reindex(df.index).fillna(False)

    # 歷史回測（手續費 + 滑價沿用預設）
    sim = _simulate(df, entries, exits, init_cash=100_000, fees=0.001425, slippage=0.0005)
    closed = [t for t in sim["trades"] if t.get("exit_date") is not None]
    if len(closed) < 3:
        return None  # 樣本太少，期望值不可信

    wins = [t for t in closed if (t.get("return_pct") or 0) > 0]
    losses = [t for t in closed if (t.get("return_pct") or 0) <= 0]
    win_rate = len(wins) / len(closed)
    avg_win = float(np.mean([t["return_pct"] for t in wins])) if wins else 0.0
    avg_loss = float(np.mean([t["return_pct"] for t in losses])) if losses else 0.0
    expected_return = win_rate * avg_win + (1 - win_rate) * avg_loss
    max_dd = sim["metrics"].get("max_drawdown") or 0.0

    # 訊號偵測：最近 RECENT_WINDOW_DAYS 內是否有 entry True
    recent_entries = entries.iloc[-RECENT_WINDOW_DAYS:]
    if not bool(recent_entries.any()):
        return None
    signal_idx = recent_entries[recent_entries].index[-1]

    return {
        "symbol": symbol,
        "name": name,
        "market": market,
        "horizon": horizon,
        "strategy": strategy_name,
        "signal_date": signal_idx.strftime("%Y-%m-%d"),
        "last_close": _safe_pct(float(df["close"].iloc[-1])),
        "win_rate": _safe_pct(win_rate),
        "avg_win_pct": _safe_pct(avg_win),
        "avg_loss_pct": _safe_pct(avg_loss),
        "expected_return_pct": _safe_pct(expected_return),
        "n_trades": len(closed),
        "max_drawdown_pct": _safe_pct(max_dd),
    }


def scan(
    db: Session,
    horizon: int,
    universe_kind: str = "top500",
    on_progress: Callable[[int, int, int], None] | None = None,
    max_workers: int = 6,
) -> dict:
    """同步掃描（背景任務會在執行緒裡呼叫）。"""
    if horizon not in HORIZON_STRATEGY:
        raise ValueError(f"unknown horizon: {horizon}")

    from app.data import universe

    if universe_kind == "top500":
        symbols = universe.top_n(db, 500)
    elif universe_kind == "tw":
        symbols = universe.all_symbols(db, "TW")
    elif universe_kind == "us":
        symbols = universe.all_symbols(db, "US")
    elif universe_kind == "all":
        symbols = universe.all_symbols(db, "ALL")
    else:
        raise ValueError(f"unknown universe: {universe_kind}")

    name_map: dict[str, tuple[str | None, str | None]] = {}
    for s in db.query(orm.Stock).all():
        name_map[s.symbol] = (s.name, s.market)

    total = len(symbols)
    matched = 0
    results: list[dict] = []
    scanned = 0

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(_evaluate_one, sym, horizon, *name_map.get(sym, (None, None))): sym
            for sym in symbols
        }
        for fut in as_completed(futures):
            scanned += 1
            try:
                r = fut.result()
            except Exception:
                r = None
            if r is not None:
                results.append(r)
                matched += 1
            if on_progress is not None and scanned % 5 == 0:
                on_progress(scanned, matched, total)

    if on_progress is not None:
        on_progress(scanned, matched, total)

    results.sort(key=lambda x: x["expected_return_pct"], reverse=True)
    return {"horizon": horizon, "scanned": scanned, "matched": matched, "total": total, "results": results}


def save_run(db: Session, run_id: int, results: list[dict], user_id: int = 1) -> None:
    db.query(orm.Recommendation).filter(
        orm.Recommendation.run_id == run_id, orm.Recommendation.user_id == user_id
    ).delete()
    now = datetime.utcnow()
    for r in results:
        db.add(
            orm.Recommendation(
                run_id=run_id,
                user_id=user_id,
                horizon=r["horizon"],
                symbol=r["symbol"],
                name=r.get("name"),
                market=r.get("market"),
                strategy=r["strategy"],
                signal_date=r["signal_date"],
                last_close=r["last_close"],
                win_rate=r["win_rate"],
                avg_win_pct=r["avg_win_pct"],
                avg_loss_pct=r["avg_loss_pct"],
                expected_return_pct=r["expected_return_pct"],
                n_trades=r["n_trades"],
                max_drawdown_pct=r["max_drawdown_pct"],
                computed_at=now,
            )
        )
    db.commit()


def latest_run(db: Session, horizon: int, user_id: int = 1) -> orm.RecommendationRun | None:
    return (
        db.query(orm.RecommendationRun)
        .filter(
            orm.RecommendationRun.horizon == horizon,
            orm.RecommendationRun.user_id == user_id,
            orm.RecommendationRun.status == "done",
        )
        .order_by(orm.RecommendationRun.finished_at.desc())
        .first()
    )


def list_recommendations(
    db: Session, run_id: int, limit: int = 30, user_id: int = 1
) -> list[dict]:
    rows = (
        db.query(orm.Recommendation)
        .filter(orm.Recommendation.run_id == run_id, orm.Recommendation.user_id == user_id)
        .order_by(orm.Recommendation.expected_return_pct.desc())
        .limit(limit)
        .all()
    )
    # 名稱即時 join 自 stocks 表（避免 cached 結果裡 name 為 null）
    syms = [r.symbol for r in rows]
    name_map: dict[str, str] = {}
    if syms:
        for s in db.query(orm.Stock).filter(orm.Stock.symbol.in_(syms)):
            if s.name:
                name_map[s.symbol] = s.name

    out = []
    for r in rows:
        item = {
            "symbol": r.symbol,
            "name": name_map.get(r.symbol) or r.name,
            "market": r.market,
            "horizon": r.horizon,
            "strategy": r.strategy,
            "signal_date": r.signal_date,
            "last_close": r.last_close,
            "win_rate": r.win_rate,
            "avg_win_pct": r.avg_win_pct,
            "avg_loss_pct": r.avg_loss_pct,
            "expected_return_pct": r.expected_return_pct,
            "n_trades": r.n_trades,
            "max_drawdown_pct": r.max_drawdown_pct,
        }
        # 補上預期目標 / 停損價（純數學，不打外部 API）
        if r.last_close and r.avg_win_pct is not None and r.avg_loss_pct is not None:
            item["target_high"] = round(r.last_close * (1 + r.avg_win_pct / 100.0), 4)
            item["target_low"] = round(r.last_close * (1 + r.avg_loss_pct / 100.0), 4)
            item["risk_reward_ratio"] = (
                round(abs(r.avg_win_pct / r.avg_loss_pct), 2) if r.avg_loss_pct else None
            )
        out.append(item)
    return out
