"""綜合評分儀表板：把各種訊號加權成「推薦買入 / 持平 / 不建議」。

刻意做成純規則式（Karpathy 第 5 條：deterministic 工作放在 code）。
不打 LLM、不依賴模型，每次同樣輸入產生同樣輸出。

評分構成（總和 -100 ~ +100）：

  1. 策略期望值     30%   — 5 個持有期 prediction 的中位數期望報酬
  2. 短/中期動能    20%   — 近 1 個月 / 3 個月報酬
  3. 籌碼面         25%   — TW: 5/20 日三大法人淨流向；US: insider 近期淨方向
  4. MFI 過熱/超賣  15%   — MFI < 20 強買；MFI > 80 過熱
  5. 量能異常       10%   — vol_z > 2 + 上漲 → 加分；下跌則減分

最終分桶：
  >= +50  強烈推薦買入
  +20..50 推薦買入
  -20..20 持平觀望
  -50..-20 不建議買入
  <= -50  強烈避開
"""
from __future__ import annotations

import logging

import numpy as np

from app.data import fetcher, fund_flow
from app.services import prediction_service

logger = logging.getLogger(__name__)


def _clip(v: float, lo: float = -100, hi: float = 100) -> float:
    return max(lo, min(hi, v))


def _bucket(score: float) -> tuple[str, str, str]:
    """回傳 (level_key, level_label, color)."""
    if score >= 50:
        return "strong_buy", "強烈推薦買入", "#10b981"
    if score >= 20:
        return "buy", "推薦買入", "#22c55e"
    if score >= -20:
        return "hold", "持平觀望", "#94a3b8"
    if score >= -50:
        return "avoid", "不建議買入", "#f97316"
    return "strong_avoid", "強烈避開", "#ef4444"


def _score_predictions(pred_payload: dict) -> tuple[float, dict]:
    preds = pred_payload.get("predictions", [])
    valid = [
        p for p in preds
        if p.get("expected_return_pct") is not None and p.get("n_trades", 0) >= 3
    ]
    if not valid:
        return 0.0, {"available": False, "reason": "無充足歷史樣本"}

    er_med = float(np.median([p["expected_return_pct"] for p in valid]))
    # +5% → +100, -5% → -100
    raw = _clip(er_med * 20)

    # 有當前訊號加權
    has_any_signal = any(p.get("has_signal_now") for p in valid)
    if has_any_signal:
        raw = _clip(raw + 15)

    return raw, {
        "available": True,
        "median_expected_pct": round(er_med, 2),
        "has_signal_now": has_any_signal,
        "n_horizons": len(valid),
    }


def _score_momentum(symbol: str) -> tuple[float, dict]:
    df = fetcher.get_ohlcv(symbol, period="1y")
    if df is None or df.empty or len(df) < 70:
        return 0.0, {"available": False}

    close = df["close"]
    last = float(close.iloc[-1])

    def ret(days: int) -> float | None:
        if len(close) < days + 1:
            return None
        prev = float(close.iloc[-(days + 1)])
        if prev == 0:
            return None
        return (last / prev - 1) * 100

    r1m = ret(21)
    r3m = ret(63)
    parts = [x for x in (r1m, r3m) if x is not None]
    if not parts:
        return 0.0, {"available": False}

    avg = float(np.mean(parts))
    # +10% → +100, -10% → -100
    raw = _clip(avg * 10)
    return raw, {
        "available": True,
        "return_1m_pct": round(r1m, 2) if r1m is not None else None,
        "return_3m_pct": round(r3m, 2) if r3m is not None else None,
    }


def _score_fund_flow(symbol: str, market: str) -> tuple[float, dict]:
    if market == "TW":
        rows = fund_flow.get_tw_institutional(symbol, days=30)
        if not rows:
            return 0.0, {"available": False, "reason": "無法人資料"}

        def sum_recent(n: int) -> float:
            recent = rows[-n:] if len(rows) >= n else rows
            total = 0.0
            for r in recent:
                for k in ("foreign_net", "trust_net", "dealer_net"):
                    v = r.get(k)
                    if v is not None:
                        total += float(v)
            return total

        net5 = sum_recent(5)
        net20 = sum_recent(20)

        # 用 OHLCV 平均成交量做正規化（百分比意義較直觀）
        df = fetcher.get_ohlcv(symbol, period="3mo")
        if df is None or df.empty or "volume" not in df.columns:
            avg_vol = 1.0
        else:
            avg_vol = float(df["volume"].tail(20).mean()) or 1.0

        ratio_5 = net5 / avg_vol  # 累積買超佔近 20 日平均成交量幾倍
        # ratio = 5 (五天買超累積等於 5 天的平均量) → +100
        raw = _clip(ratio_5 * 20)
        return raw, {
            "available": True,
            "net5_shares": int(net5),
            "net20_shares": int(net20),
            "avg_volume": int(avg_vol),
            "ratio_5d": round(ratio_5, 2),
        }
    else:
        # US：用 insider transactions 近 20 筆的方向（買 vs 賣）
        rows = fund_flow.get_us_insider(symbol, limit=20) if hasattr(fund_flow, "get_us_insider") else []
        if not rows:
            return 0.0, {"available": False, "reason": "無 insider 資料"}
        buys = sum(1 for r in rows if (r.get("transaction") or "").lower().startswith("buy") or (r.get("shares") or 0) > 0)
        sells = sum(1 for r in rows if (r.get("transaction") or "").lower().startswith("sale") or (r.get("transaction") or "").lower().startswith("sell"))
        total = buys + sells
        if total == 0:
            return 0.0, {"available": False}
        net_ratio = (buys - sells) / total
        raw = _clip(net_ratio * 60)
        return raw, {
            "available": True,
            "insider_buys": buys,
            "insider_sells": sells,
        }


def _score_mfi(indicators: list[dict]) -> tuple[float, dict]:
    if not indicators:
        return 0.0, {"available": False}
    mfi_values = [r.get("mfi") for r in indicators[-5:] if r.get("mfi") is not None]
    if not mfi_values:
        return 0.0, {"available": False}
    last_mfi = float(mfi_values[-1])

    if last_mfi < 20:
        raw = 80.0
    elif last_mfi < 40:
        raw = 30.0
    elif last_mfi <= 60:
        raw = 0.0
    elif last_mfi <= 80:
        raw = -30.0
    else:
        raw = -80.0

    return raw, {"available": True, "mfi": round(last_mfi, 1)}


def _score_volume(indicators: list[dict]) -> tuple[float, dict]:
    if not indicators or len(indicators) < 2:
        return 0.0, {"available": False}
    last = indicators[-1]
    prev = indicators[-2]
    z = last.get("vol_z")
    c_now = last.get("close")
    c_prev = prev.get("close")
    if z is None or c_now is None or c_prev is None:
        return 0.0, {"available": False}

    z = float(z)
    direction_up = c_now > c_prev

    if z >= 2.0:
        raw = 50.0 if direction_up else -30.0
    elif z >= 1.0:
        raw = 20.0 if direction_up else -10.0
    elif z <= -1.5:
        raw = -10.0
    else:
        raw = 0.0

    return raw, {
        "available": True,
        "vol_z": round(z, 2),
        "direction_up": direction_up,
    }


WEIGHTS = {
    "predictions": 0.30,
    "momentum": 0.20,
    "fund_flow": 0.25,
    "mfi": 0.15,
    "volume": 0.10,
}


ENTRY_MODES = {
    "conservative": "保守：等較深回檔",
    "balanced": "平衡：ATR 回檔區",
    "aggressive": "積極：允許小幅追價",
    "sma_pullback": "均線回測：靠近 SMA20/60",
}


def _sma_pullback_range(symbol: str, last_close: float, atr: float | None) -> tuple[float, float] | None:
    """用 SMA20 / SMA60 當回測買進區間；取最接近現價且不為空的均線。"""
    try:
        df = fetcher.get_ohlcv(symbol, period="1y")
    except Exception as e:
        logger.debug("sma pullback range failed %s: %s", symbol, e)
        return None
    if df is None or df.empty or "close" not in df.columns:
        return None

    close = df["close"]
    candidates: list[float] = []
    for window in (20, 60):
        if len(close) >= window:
            v = close.rolling(window).mean().iloc[-1]
            if np.isfinite(v) and v > 0:
                candidates.append(float(v))
    if not candidates:
        return None

    center = min(candidates, key=lambda x: abs(last_close - x))
    band = (atr * 0.25) if atr and atr > 0 else center * 0.01
    return center - band, center + band


def _entry_range(
    symbol: str, last_close: float, atr: float | None, entry_mode: str
) -> tuple[float, float, str, str]:
    """回傳 (buy_low, buy_high, normalized_mode, mode_label)。"""
    mode = entry_mode if entry_mode in ENTRY_MODES else "balanced"

    if mode == "conservative":
        if atr and atr > 0:
            return last_close - 1.0 * atr, last_close - 0.2 * atr, mode, ENTRY_MODES[mode]
        return last_close * 0.97, last_close * 0.995, mode, ENTRY_MODES[mode]

    if mode == "aggressive":
        if atr and atr > 0:
            return last_close, last_close + 0.8 * atr, mode, ENTRY_MODES[mode]
        return last_close, last_close * 1.02, mode, ENTRY_MODES[mode]

    if mode == "sma_pullback":
        rng = _sma_pullback_range(symbol, last_close, atr)
        if rng is not None:
            return rng[0], rng[1], mode, ENTRY_MODES[mode]
        mode = "balanced"

    # balanced：沿用原本的「回檔為主、可小幅追價」
    if atr and atr > 0:
        return last_close - 0.5 * atr, last_close + 0.3 * atr, mode, ENTRY_MODES[mode]
    return last_close * 0.98, last_close * 1.01, mode, ENTRY_MODES[mode]


def _build_suggestion(
    symbol: str, pred_payload: dict, level_key: str, entry_mode: str = "balanced"
) -> dict | None:
    """根據歷史回測 + 使用者選擇的進場策略，給出買進區間 / 目標價 / 停損。

    目標價 / 停損 = 各持有期策略的 target_high / target_low 中位數。
    買進區間 = entry_mode 決定，預設為 balanced。
    """
    last_close = pred_payload.get("last_close")
    atr = pred_payload.get("atr")
    valid = [
        p for p in pred_payload.get("predictions", [])
        if p.get("target_high") is not None
        and p.get("target_low") is not None
        and p.get("n_trades", 0) >= 3
    ]
    if last_close is None or not valid:
        return None

    last_close = float(last_close)
    atr_val = float(atr) if atr is not None else None
    target_high = float(np.median([p["target_high"] for p in valid]))
    target_low = float(np.median([p["target_low"] for p in valid]))
    upside_pct = (target_high / last_close - 1) * 100
    downside_pct = (target_low / last_close - 1) * 100

    buy_low, buy_high, normalized_mode, mode_label = _entry_range(
        symbol, last_close, atr_val, entry_mode
    )

    # 動作建議文字會跟 verdict level 綁定
    action_map = {
        "strong_buy": ("立刻分批進場", "買進區間內可分 2~3 批進場"),
        "buy": ("逢拉回分批進場", f"建議在 {buy_low:.2f} 附近等回檔買進"),
        "hold": ("觀望，等更好價位", f"等回到 {buy_low:.2f} 以下再考慮"),
        "avoid": ("不建議買進", "目前訊號偏弱，避免攤平"),
        "strong_avoid": ("避開或減碼", "明確賣出訊號，不應進場"),
    }
    action, hint = action_map.get(level_key, ("觀望", ""))

    return {
        "entry_price": round(last_close, 2),
        "entry_mode": normalized_mode,
        "entry_mode_label": mode_label,
        "buy_low": round(buy_low, 2),
        "buy_high": round(buy_high, 2),
        "target_price": round(target_high, 2),
        "stop_loss": round(target_low, 2),
        "upside_pct": round(upside_pct, 2),
        "downside_pct": round(downside_pct, 2),
        "risk_reward_ratio": (
            round(abs(upside_pct / downside_pct), 2) if downside_pct else None
        ),
        "action": action,
        "hint": hint,
        "n_strategies_used": len(valid),
    }


def evaluate(symbol: str, entry_mode: str = "balanced") -> dict:
    symbol = fetcher.normalize_symbol(symbol)
    market = fetcher.detect_market(symbol)

    # 取所有需要的原始資料
    try:
        pred_payload = prediction_service.for_stock(symbol)
    except Exception as e:
        logger.warning("prediction failed %s: %s", symbol, e)
        pred_payload = {"predictions": []}

    try:
        ff = fund_flow.get_fund_flow(symbol)
    except Exception as e:
        logger.warning("fund flow failed %s: %s", symbol, e)
        ff = {"indicators": [], "tw_institutional": [], "us_insider": []}
    indicators = ff.get("indicators", []) or []

    # 五個分項
    sub_scores: list[dict] = []
    total = 0.0
    weight_used = 0.0

    score, detail = _score_predictions(pred_payload)
    sub_scores.append({
        "key": "predictions",
        "label": "策略期望值",
        "raw_score": round(score, 1),
        "weight": WEIGHTS["predictions"],
        "weighted": round(score * WEIGHTS["predictions"], 1),
        "detail": detail,
    })
    if detail.get("available"):
        total += score * WEIGHTS["predictions"]
        weight_used += WEIGHTS["predictions"]

    score, detail = _score_momentum(symbol)
    sub_scores.append({
        "key": "momentum",
        "label": "短中期動能",
        "raw_score": round(score, 1),
        "weight": WEIGHTS["momentum"],
        "weighted": round(score * WEIGHTS["momentum"], 1),
        "detail": detail,
    })
    if detail.get("available"):
        total += score * WEIGHTS["momentum"]
        weight_used += WEIGHTS["momentum"]

    score, detail = _score_fund_flow(symbol, market)
    sub_scores.append({
        "key": "fund_flow",
        "label": "籌碼面" if market == "TW" else "Insider 動向",
        "raw_score": round(score, 1),
        "weight": WEIGHTS["fund_flow"],
        "weighted": round(score * WEIGHTS["fund_flow"], 1),
        "detail": detail,
    })
    if detail.get("available"):
        total += score * WEIGHTS["fund_flow"]
        weight_used += WEIGHTS["fund_flow"]

    score, detail = _score_mfi(indicators)
    sub_scores.append({
        "key": "mfi",
        "label": "MFI 資金流量",
        "raw_score": round(score, 1),
        "weight": WEIGHTS["mfi"],
        "weighted": round(score * WEIGHTS["mfi"], 1),
        "detail": detail,
    })
    if detail.get("available"):
        total += score * WEIGHTS["mfi"]
        weight_used += WEIGHTS["mfi"]

    score, detail = _score_volume(indicators)
    sub_scores.append({
        "key": "volume",
        "label": "量能異常",
        "raw_score": round(score, 1),
        "weight": WEIGHTS["volume"],
        "weighted": round(score * WEIGHTS["volume"], 1),
        "detail": detail,
    })
    if detail.get("available"):
        total += score * WEIGHTS["volume"]
        weight_used += WEIGHTS["volume"]

    # 用「實際使用權重」正規化，避免缺資料時被嚴重低估
    final_score = total / weight_used if weight_used > 0 else 0.0
    final_score = round(_clip(final_score), 1)
    level_key, level_label, color = _bucket(final_score)

    suggestion = _build_suggestion(symbol, pred_payload, level_key, entry_mode)

    return {
        "symbol": symbol,
        "market": market,
        "score": final_score,
        "level": level_key,
        "level_label": level_label,
        "color": color,
        "weight_used": round(weight_used, 2),
        "components": sub_scores,
        "suggestion": suggestion,
    }
