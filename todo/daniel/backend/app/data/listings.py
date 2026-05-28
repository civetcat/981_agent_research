"""抓取台股 + 美股完整 listings 並寫入 stocks 表。

資料源：
- TW 上市：TWSE OpenAPI t187ap03_L
- TW 上櫃：TPEX OpenAPI mainboard
- US 全部：Nasdaq Trader 公開檔（nasdaqlisted.txt + otherlisted.txt）

重複呼叫安全（upsert by symbol）。
"""
from __future__ import annotations

import logging

import httpx
from sqlalchemy.orm import Session

from app.models import db as orm

logger = logging.getLogger(__name__)

TWSE_LISTED_URL = "https://openapi.twse.com.tw/v1/opendata/t187ap03_L"
TPEX_LISTED_URL = "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes"
NASDAQ_LISTED_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
OTHER_LISTED_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"


def _upsert_stock(db: Session, **fields) -> None:
    sym = fields["symbol"]
    existing = db.query(orm.Stock).filter(orm.Stock.symbol == sym).first()
    if existing:
        for k, v in fields.items():
            if v is not None:
                setattr(existing, k, v)
    else:
        db.add(orm.Stock(**fields))


def fetch_tw_listed(db: Session) -> int:
    """台股上市。回傳新增/更新筆數。"""
    try:
        r = httpx.get(TWSE_LISTED_URL, timeout=30)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        logger.error("TWSE listed fetch failed: %s", e)
        return 0

    n = 0
    for row in data:
        code = (row.get("公司代號") or "").strip()
        name = (row.get("公司名稱") or row.get("公司簡稱") or "").strip()
        sector = (row.get("產業別") or "").strip() or None
        if not code or not code.isdigit():
            continue
        _upsert_stock(
            db,
            symbol=f"{code}.TW",
            name=name,
            market="TW",
            exchange="TWSE",
            sector=sector,
            is_etf=0,
        )
        n += 1
    db.commit()
    return n


def fetch_tw_otc(db: Session) -> int:
    """台股上櫃。"""
    try:
        r = httpx.get(TPEX_LISTED_URL, timeout=30)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        logger.error("TPEX listed fetch failed: %s", e)
        return 0

    n = 0
    for row in data:
        code = (row.get("SecuritiesCompanyCode") or "").strip()
        name = (row.get("CompanyName") or "").strip()
        if not code or not code.isdigit():
            continue
        _upsert_stock(
            db,
            symbol=f"{code}.TWO",
            name=name,
            market="TW",
            exchange="TPEX",
            is_etf=0,
        )
        n += 1
    db.commit()
    return n


def _parse_pipe_psv(text: str) -> list[dict]:
    """Nasdaq Trader 用 | 分隔，最後一行是 File Creation Time。"""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return []
    if lines[-1].lower().startswith("file creation"):
        lines = lines[:-1]
    header = lines[0].split("|")
    rows = []
    for ln in lines[1:]:
        parts = ln.split("|")
        if len(parts) != len(header):
            continue
        rows.append(dict(zip(header, parts)))
    return rows


def fetch_us(db: Session) -> int:
    """美股全部（Nasdaq + NYSE + AMEX）。"""
    n = 0
    for url, exchange_field in [(NASDAQ_LISTED_URL, None), (OTHER_LISTED_URL, "Exchange")]:
        try:
            r = httpx.get(url, timeout=30, follow_redirects=True)
            r.raise_for_status()
            rows = _parse_pipe_psv(r.text)
        except Exception as e:
            logger.error("US listings fetch failed (%s): %s", url, e)
            continue

        for row in rows:
            sym = (row.get("Symbol") or row.get("ACT Symbol") or "").strip()
            name = (row.get("Security Name") or "").strip()
            test_issue = (row.get("Test Issue") or "N").strip()
            etf = (row.get("ETF") or "N").strip()
            if not sym or test_issue == "Y":
                continue
            # skip preferred / warrants / units (含特殊符號)
            if any(c in sym for c in ("$", ".", "=")):
                continue

            exchange = (row.get(exchange_field) or "NASDAQ").strip() if exchange_field else "NASDAQ"
            exchange_map = {"N": "NYSE", "A": "AMEX", "P": "ARCA", "Z": "BATS", "V": "IEX"}
            exchange = exchange_map.get(exchange, exchange)

            _upsert_stock(
                db,
                symbol=sym,
                name=name,
                market="US",
                exchange=exchange,
                is_etf=1 if etf == "Y" else 0,
            )
            n += 1

    db.commit()
    return n


def fetch_all(db: Session) -> dict:
    return {
        "tw_listed": fetch_tw_listed(db),
        "tw_otc": fetch_tw_otc(db),
        "us": fetch_us(db),
    }


# ---- Top-N 流動性內建清單（首次 / 快速使用，不依賴外部 API） ----

# (symbol, 中文/英文名稱)
TW_TOP: list[tuple[str, str]] = [
    ("2330.TW", "台積電"), ("2317.TW", "鴻海"), ("2454.TW", "聯發科"),
    ("2308.TW", "台達電"), ("2412.TW", "中華電"), ("2881.TW", "富邦金"),
    ("2882.TW", "國泰金"), ("2891.TW", "中信金"), ("2884.TW", "玉山金"),
    ("2886.TW", "兆豐金"), ("1301.TW", "台塑"), ("1303.TW", "南亞"),
    ("2002.TW", "中鋼"), ("1216.TW", "統一"), ("1101.TW", "台泥"),
    ("1102.TW", "亞泥"), ("2207.TW", "和泰車"), ("2105.TW", "正新"),
    ("2912.TW", "統一超"), ("2382.TW", "廣達"), ("3008.TW", "大立光"),
    ("3711.TW", "日月光投控"), ("3034.TW", "聯詠"), ("2357.TW", "華碩"),
    ("2303.TW", "聯電"), ("2379.TW", "瑞昱"), ("2603.TW", "長榮"),
    ("2609.TW", "陽明"), ("2615.TW", "萬海"), ("2618.TW", "長榮航"),
    ("1605.TW", "華新"), ("2027.TW", "大成鋼"), ("2474.TW", "可成"),
    ("3017.TW", "奇鋐"), ("3231.TW", "緯創"), ("3661.TW", "世芯-KY"),
    ("4938.TW", "和碩"), ("5871.TW", "中租-KY"), ("5880.TW", "合庫金"),
    ("6505.TW", "台塑化"), ("6669.TW", "緯穎"), ("8046.TW", "南電"),
    ("8454.TW", "富邦媒"), ("9910.TW", "豐泰"), ("9921.TW", "巨大"),
    ("2885.TW", "元大金"), ("2887.TW", "台新金"), ("2890.TW", "永豐金"),
    ("2892.TW", "第一金"), ("0050.TW", "元大台灣50"), ("0056.TW", "元大高股息"),
    ("00878.TW", "國泰永續高股息"), ("00881.TW", "國泰台灣5G+"),
    ("00919.TW", "群益台灣精選高息"), ("00929.TW", "復華台灣科技優息"),
    ("00940.TW", "元大臺灣價值高息"), ("2345.TW", "智邦"), ("3045.TW", "台灣大"),
    ("2376.TW", "技嘉"), ("2356.TW", "英業達"), ("3037.TW", "欣興"),
    ("2227.TW", "裕日車"), ("2354.TW", "鴻準"), ("2395.TW", "研華"),
    ("3653.TW", "健策"), ("4904.TW", "遠傳"), ("6488.TW", "環球晶"),
    ("8112.TW", "至上"), ("9914.TW", "美利達"),
]

US_TOP: list[tuple[str, str]] = [
    ("AAPL", "Apple"), ("MSFT", "Microsoft"), ("GOOGL", "Alphabet A"),
    ("GOOG", "Alphabet C"), ("AMZN", "Amazon"), ("NVDA", "NVIDIA"),
    ("META", "Meta Platforms"), ("TSLA", "Tesla"), ("BRK-B", "Berkshire Hathaway B"),
    ("JPM", "JPMorgan Chase"), ("V", "Visa"), ("UNH", "UnitedHealth"),
    ("WMT", "Walmart"), ("JNJ", "Johnson & Johnson"), ("PG", "Procter & Gamble"),
    ("MA", "Mastercard"), ("HD", "Home Depot"), ("ORCL", "Oracle"),
    ("AVGO", "Broadcom"), ("BAC", "Bank of America"), ("LLY", "Eli Lilly"),
    ("KO", "Coca-Cola"), ("ADBE", "Adobe"), ("CRM", "Salesforce"),
    ("NFLX", "Netflix"), ("CSCO", "Cisco"), ("PEP", "PepsiCo"), ("AMD", "AMD"),
    ("INTC", "Intel"), ("TMO", "Thermo Fisher"), ("MRK", "Merck"),
    ("ABT", "Abbott"), ("WFC", "Wells Fargo"), ("DIS", "Disney"),
    ("PFE", "Pfizer"), ("VZ", "Verizon"), ("CMCSA", "Comcast"), ("NKE", "Nike"),
    ("ABBV", "AbbVie"), ("T", "AT&T"), ("QCOM", "Qualcomm"),
    ("TXN", "Texas Instruments"), ("MCD", "McDonald's"), ("BA", "Boeing"),
    ("GS", "Goldman Sachs"), ("AMGN", "Amgen"), ("HON", "Honeywell"),
    ("IBM", "IBM"), ("LIN", "Linde"), ("UPS", "UPS"), ("CAT", "Caterpillar"),
    ("RTX", "RTX"), ("DE", "Deere"), ("BLK", "BlackRock"), ("SBUX", "Starbucks"),
    ("GE", "GE Aerospace"), ("AXP", "American Express"), ("LOW", "Lowe's"),
    ("MS", "Morgan Stanley"), ("C", "Citigroup"), ("MDT", "Medtronic"),
    ("UNP", "Union Pacific"), ("INTU", "Intuit"), ("GILD", "Gilead"),
    ("PYPL", "PayPal"), ("BKNG", "Booking"), ("ADI", "Analog Devices"),
    ("ISRG", "Intuitive Surgical"), ("VRTX", "Vertex"), ("REGN", "Regeneron"),
    ("PLTR", "Palantir"), ("PANW", "Palo Alto Networks"), ("MELI", "MercadoLibre"),
    ("MAR", "Marriott"), ("SNOW", "Snowflake"), ("SHOP", "Shopify"),
    ("DASH", "DoorDash"), ("ABNB", "Airbnb"), ("UBER", "Uber"), ("COIN", "Coinbase"),
    ("SPY", "S&P 500 ETF"), ("QQQ", "Nasdaq 100 ETF"), ("VOO", "Vanguard S&P 500"),
    ("IWM", "Russell 2000 ETF"), ("DIA", "Dow 30 ETF"), ("VTI", "Vanguard Total Market"),
    ("VEA", "Vanguard FTSE Developed"), ("VWO", "Vanguard Emerging Markets"),
    ("BND", "Vanguard Total Bond"), ("GLD", "SPDR Gold"),
    ("ARKK", "ARK Innovation"), ("TLT", "20+ Year Treasury"),
    ("XLE", "Energy Select"), ("XLF", "Financial Select"),
    ("XLK", "Technology Select"), ("XLV", "Health Care Select"),
    ("XLY", "Consumer Discretionary"), ("XLI", "Industrial Select"),
    ("XLU", "Utilities Select"), ("XLP", "Consumer Staples Select"),
]


def seed_top(db: Session) -> int:
    """灌入 Top 流動性清單（含名稱）。"""
    seen: set[str] = set()
    n = 0
    for sym, name in TW_TOP:
        if sym in seen:
            continue
        seen.add(sym)
        _upsert_stock(
            db, symbol=sym, name=name, market="TW", exchange="TWSE", liquidity_rank=n
        )
        n += 1
    for sym, name in US_TOP:
        if sym in seen:
            continue
        seen.add(sym)
        _upsert_stock(
            db, symbol=sym, name=name, market="US", exchange="NASDAQ", liquidity_rank=n
        )
        n += 1
    db.commit()
    return n


def enrich_names(db: Session) -> int:
    """補上既有 stocks 的名稱（不新增 symbol）。"""
    name_map: dict[str, str] = {}
    for sym, nm in TW_TOP:
        name_map[sym] = nm
    for sym, nm in US_TOP:
        name_map[sym] = nm

    n = 0
    for s in db.query(orm.Stock).filter((orm.Stock.name.is_(None)) | (orm.Stock.name == "")):
        nm = name_map.get(s.symbol)
        if nm:
            s.name = nm
            n += 1
    if n:
        db.commit()
    return n
