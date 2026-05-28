"""策劃過的主流 ETF 清單。

不打算自動抓「所有 ETF」——一來資料源不穩，二來大部分人關心的就是這些主流商品。
分類粗略：
  market_index  市值型大盤（追蹤台灣 50 / S&P500 等）
  high_yield    高股息
  thematic      產業/主題（半導體、5G、ARK 等）
  bond          債券
  reits_gold    REITs / 黃金 / 商品
  international 海外/區域型
"""
from __future__ import annotations

# (symbol, name, category)
TW_ETFS: list[tuple[str, str, str]] = [
    # 市值型
    ("0050.TW", "元大台灣50", "market_index"),
    ("006208.TW", "富邦台50", "market_index"),
    ("00692.TW", "富邦公司治理", "market_index"),
    ("00850.TW", "元大臺灣ESG永續", "market_index"),
    # 高股息
    ("0056.TW", "元大高股息", "high_yield"),
    ("00878.TW", "國泰永續高股息", "high_yield"),
    ("00919.TW", "群益台灣精選高息", "high_yield"),
    ("00929.TW", "復華台灣科技優息", "high_yield"),
    ("00713.TW", "元大台灣高息低波", "high_yield"),
    ("00940.TW", "元大臺灣價值高息", "high_yield"),
    ("00939.TW", "統一台灣高息動能", "high_yield"),
    ("00713.TW", "元大台灣高息低波", "high_yield"),
    # 產業 / 主題
    ("00881.TW", "國泰台灣5G+", "thematic"),
    ("00891.TW", "中信關鍵半導體", "thematic"),
    ("00892.TW", "富邦台灣半導體", "thematic"),
    ("0052.TW", "富邦科技", "thematic"),
    ("00876.TW", "元大全球5G", "thematic"),
    # 海外 / 區域
    ("00646.TW", "元大S&P500", "international"),
    ("00662.TW", "富邦NASDAQ", "international"),
    ("00757.TW", "統一FANG+", "international"),
    ("00712.TW", "復華富時不動產", "reits_gold"),
    ("00635U.TW", "期元大S&P黃金", "reits_gold"),
    # 債券
    ("00679B.TW", "元大美債20年", "bond"),
    ("00687B.TW", "國泰20年美債", "bond"),
    ("00772B.TW", "中信高評級公司債", "bond"),
]

US_ETFS: list[tuple[str, str, str]] = [
    # 市值型
    ("SPY", "SPDR S&P 500", "market_index"),
    ("VOO", "Vanguard S&P 500", "market_index"),
    ("IVV", "iShares Core S&P 500", "market_index"),
    ("VTI", "Vanguard Total Stock Market", "market_index"),
    ("QQQ", "Invesco QQQ Trust (Nasdaq-100)", "market_index"),
    ("DIA", "SPDR Dow Jones", "market_index"),
    # 高股息 / 價值
    ("SCHD", "Schwab US Dividend Equity", "high_yield"),
    ("VYM", "Vanguard High Dividend Yield", "high_yield"),
    ("VIG", "Vanguard Dividend Appreciation", "high_yield"),
    ("VTV", "Vanguard Value", "high_yield"),
    ("HDV", "iShares Core High Dividend", "high_yield"),
    # 產業 / 主題
    ("SMH", "VanEck Semiconductor", "thematic"),
    ("SOXX", "iShares Semiconductor", "thematic"),
    ("XLK", "Technology Select Sector", "thematic"),
    ("XLE", "Energy Select Sector", "thematic"),
    ("XLF", "Financial Select Sector", "thematic"),
    ("XLV", "Health Care Select Sector", "thematic"),
    ("ARKK", "ARK Innovation", "thematic"),
    # 國際
    ("VEA", "Vanguard Developed Markets", "international"),
    ("VWO", "Vanguard Emerging Markets", "international"),
    ("EFA", "iShares MSCI EAFE", "international"),
    ("IEMG", "iShares Core MSCI Emerging Markets", "international"),
    # 債券
    ("BND", "Vanguard Total Bond Market", "bond"),
    ("AGG", "iShares Core US Aggregate Bond", "bond"),
    ("TLT", "iShares 20+ Year Treasury", "bond"),
    ("HYG", "iShares iBoxx High Yield", "bond"),
    # REITs / 黃金 / 商品
    ("VNQ", "Vanguard Real Estate", "reits_gold"),
    ("GLD", "SPDR Gold Trust", "reits_gold"),
    ("SLV", "iShares Silver Trust", "reits_gold"),
]


CATEGORIES = [
    ("market_index", "市值型大盤"),
    ("high_yield", "高股息 / 價值"),
    ("thematic", "產業 / 主題"),
    ("international", "海外 / 區域"),
    ("bond", "債券"),
    ("reits_gold", "REITs / 黃金 / 商品"),
]


def all_etfs() -> list[tuple[str, str, str, str]]:
    """回傳 (symbol, name, category, market) 並去重（同 symbol 只留一筆）。"""
    out: dict[str, tuple[str, str, str, str]] = {}
    for sym, name, cat in TW_ETFS:
        out.setdefault(sym, (sym, name, cat, "TW"))
    for sym, name, cat in US_ETFS:
        out.setdefault(sym, (sym, name, cat, "US"))
    return list(out.values())
