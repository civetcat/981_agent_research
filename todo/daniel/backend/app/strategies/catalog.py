"""策略目錄 + 使用建議元資料。

把後端散在 app/backtest/strategies.py 與 app/services/recommend_service.py
裡的策略全部彙整在這裡，供前端 /strategies 頁面查詢使用。
"""
from __future__ import annotations

from typing import Literal

Category = Literal["trend", "reversion", "breakout", "passive"]

CATEGORY_LABEL: dict[Category, str] = {
    "trend": "趨勢追蹤",
    "reversion": "均值回歸",
    "breakout": "突破",
    "passive": "被動長期",
}


CATALOG: list[dict] = [
    # ---- 回測頁可選的策略（key 對應 app.backtest.strategies） ----
    {
        "key": "ma_cross",
        "name": "均線黃金交叉 / 死亡交叉",
        "category": "trend",
        "horizon_days": [5, 10, 15, 30],
        "indicators": ["SMA"],
        "default_params": {"fast": 5, "slow": 20},
        "param_tips": {
            "fast": "短期均線天數，越短越敏感（雜訊也多）",
            "slow": "長期均線天數，越長越穩定（轉折也慢）",
        },
        "signal_rule": "快線（短期均線）由下向上穿越慢線 → 進場；快線下穿慢線 → 出場。",
        "when_to_use": "市場處於明顯多頭或空頭趨勢時最有效；震盪盤會被巴來巴去。",
        "best_for": [
            "有清楚趨勢的大型股（如 0050、2330、QQQ）",
            "波動度中等的個股，避免拿來跑高頻震盪股",
        ],
        "pros": ["概念直觀，最古老也最被驗證的趨勢策略", "進出邏輯機械化，沒有主觀判斷"],
        "cons": ["訊號比實際轉折落後 1-2 根 K 棒", "盤整期會頻繁假突破，連續小虧"],
        "tune_tips": "短線取 5/10，中線 5/20，中長線 20/60。fast 跟 slow 不要太接近（< 2x），否則訊號太多。",
        "use_in": "backtest",
    },
    {
        "key": "rsi_reversal",
        "name": "RSI 超買超賣反轉",
        "category": "reversion",
        "horizon_days": [5, 10],
        "indicators": ["RSI"],
        "default_params": {"low": 30, "high": 70, "window": 14},
        "param_tips": {
            "low": "進場閾值，越低越保守（要更超賣才買）",
            "high": "出場閾值，越高越貪心",
            "window": "RSI 計算週期，14 是業界標準",
        },
        "signal_rule": "RSI 跌破 low（如 30）視為超賣 → 進場；RSI 突破 high（如 70）視為超買 → 出場。",
        "when_to_use": "盤整或區間震盪市場效果最好；強趨勢中容易在「還會更超賣」的時候提早進場接刀。",
        "best_for": ["波動度高但無趨勢的標的", "藍籌股短線波段"],
        "pros": ["在區間市場勝率高", "進場價位通常較好（低買高賣）"],
        "cons": ["強趨勢中會連續虧損（『接到飛刀』）", "需要明顯支撐 / 阻力區才會有效"],
        "tune_tips": "波動高的股票把 low 調低（25）、high 調高（75）；穩定股票用標準 30/70。",
        "use_in": "backtest",
    },
    {
        "key": "bbands_breakout",
        "name": "布林通道突破",
        "category": "breakout",
        "horizon_days": [20],
        "indicators": ["Bollinger Bands"],
        "default_params": {"window": 20, "dev": 2.0},
        "param_tips": {
            "window": "通道計算週期，20 是業界標準",
            "dev": "標準差倍數，越大通道越寬、突破越罕見但更可信",
        },
        "signal_rule": "收盤價突破上軌 → 進場（順勢追多）；收盤跌破中軌（20MA） → 出場。",
        "when_to_use": "盤整壓縮後即將出現大行情、消息面突破，或股價沿著上軌前進的飆股階段。",
        "best_for": ["波動度收斂後即將釋放的標的", "突破創新高的成長股"],
        "pros": ["能捕捉大波段起點", "自動依波動度調整出入場閾值"],
        "cons": ["假突破比例不低（被洗）", "不適合長期橫盤的低波股"],
        "tune_tips": "波動大的股票把 dev 調高到 2.5，避免被假突破洗。短期看波段可改 window 10。",
        "use_in": "backtest",
    },
    {
        "key": "buy_and_hold",
        "name": "買入並持有",
        "category": "passive",
        "horizon_days": [],
        "indicators": [],
        "default_params": {},
        "param_tips": {},
        "signal_rule": "期初買入，全期持有不動。",
        "when_to_use": "你相信長期向上、不想動手，或要當作其他策略的基準對照組。",
        "best_for": ["大盤 ETF（0050、SPY、QQQ、VOO）", "長期穩定成長龍頭"],
        "pros": ["零交易成本", "適合多數人，歷史長期勝過大多數主動策略"],
        "cons": ["完整承受所有回撤（金融海嘯 -50%）", "無風險管理"],
        "tune_tips": "搭配定期定額（DCA）效果更好，但本系統 MVP 不支援。",
        "use_in": "backtest",
    },
    # ---- 推薦選股專用的策略（用於 /recommend 頁，對應 recommend_service 裡的對應） ----
    {
        "key": "sma_5_10",
        "name": "SMA 5/10 短線交叉",
        "category": "trend",
        "horizon_days": [5],
        "indicators": ["SMA"],
        "default_params": {"fast": 5, "slow": 10},
        "param_tips": {},
        "signal_rule": "5 日線上穿 10 日線 → 進場；下穿 → 出場。",
        "when_to_use": "短線波段（5 個交易日內想看到結果），最敏感、訊號最多。",
        "best_for": ["流動性高、日內波動明顯的個股"],
        "pros": ["反應快，能抓到短期動能"],
        "cons": ["假訊號多，需配合篩選器使用"],
        "tune_tips": "搭配 RSI < 70 過濾過熱進場，可提升勝率。",
        "use_in": "recommend",
    },
    {
        "key": "sma_5_20",
        "name": "SMA 5/20 中短交叉",
        "category": "trend",
        "horizon_days": [10],
        "indicators": ["SMA"],
        "default_params": {"fast": 5, "slow": 20},
        "param_tips": {},
        "signal_rule": "5 日線上穿 20 日線 → 進場；下穿 → 出場。",
        "when_to_use": "10 個交易日左右的波段操作；訊號頻率適中。",
        "best_for": ["中型股、有清楚趨勢但不是飆股的標的"],
        "pros": ["訊號密度與品質的甜蜜點", "歷史回測在多數股票上都能正收益"],
        "cons": ["強震盪盤仍有連虧風險"],
        "tune_tips": "可加上「股價站上 60 日線」過濾，避開大空頭。",
        "use_in": "recommend",
    },
    {
        "key": "sma_10_20",
        "name": "SMA 10/20 中線交叉",
        "category": "trend",
        "horizon_days": [15],
        "indicators": ["SMA"],
        "default_params": {"fast": 10, "slow": 20},
        "param_tips": {},
        "signal_rule": "10 日線上穿 20 日線 → 進場；下穿 → 出場。",
        "when_to_use": "想做半月波段（約 15 個交易日），訊號比 5/10 穩定。",
        "best_for": ["大型權值股"],
        "pros": ["雜訊較低，較適合不愛盯盤"],
        "cons": ["反應慢，會錯過急漲段的第一波"],
        "tune_tips": "搭配大盤多頭判斷（0050 站上 60 日均）效果更佳。",
        "use_in": "recommend",
    },
    {
        "key": "sma_20_60",
        "name": "SMA 20/60 長線交叉",
        "category": "trend",
        "horizon_days": [30],
        "indicators": ["SMA"],
        "default_params": {"fast": 20, "slow": 60},
        "param_tips": {},
        "signal_rule": "20 日線上穿 60 日線 → 進場；下穿 → 出場。",
        "when_to_use": "月線波段或更長，目標 1-3 個月，訊號很少但可信度高。",
        "best_for": ["龍頭股、ETF 大波段操作", "不想頻繁交易的人"],
        "pros": ["訊號可靠度高", "適合工作忙碌族群"],
        "cons": ["訊號很少，需要耐心等待", "進場時通常已漲一段"],
        "tune_tips": "出場可改用 50 日線跌破，鎖住獲利更靈活。",
        "use_in": "recommend",
    },
]


# ---- 給前端的高階建議：依「我的需求」推薦策略 ----
SCENARIOS: list[dict] = [
    {
        "scenario": "我是新手，想穩穩來",
        "recommend": "buy_and_hold",
        "reason": "先用『買入並持有』做大盤 ETF（0050 / SPY / VOO），熟悉系統與市場節奏，再學主動策略。",
    },
    {
        "scenario": "我想做短線波段（一週左右）",
        "recommend": "sma_5_10",
        "reason": "短期交叉訊號最敏感，但勝率不高，務必搭配篩選器（勝率 ≥ 45%、預期報酬 ≥ 3%）使用。",
    },
    {
        "scenario": "我想做中期波段（2–3 週）",
        "recommend": "ma_cross",
        "reason": "5/20 均線交叉是經典中短線策略，在大多頭裡勝率最好。",
    },
    {
        "scenario": "我不愛盯盤，想做月線波段",
        "recommend": "sma_20_60",
        "reason": "訊號很少但品質高，每月看一次盤就夠。",
    },
    {
        "scenario": "我覺得市場在區間震盪",
        "recommend": "rsi_reversal",
        "reason": "RSI 反轉在區間市場勝率最佳，但記得趨勢出現時要停用。",
    },
    {
        "scenario": "我覺得即將有大行情",
        "recommend": "bbands_breakout",
        "reason": "布林通道突破能抓住大波段起漲點，搭配巨量更可靠。",
    },
]


def list_catalog(category: str | None = None) -> list[dict]:
    if not category:
        return list(CATALOG)
    return [c for c in CATALOG if c["category"] == category]


def get_by_key(key: str) -> dict | None:
    for c in CATALOG:
        if c["key"] == key:
            return c
    return None
