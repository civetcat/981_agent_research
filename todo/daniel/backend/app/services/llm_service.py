"""LLM 資金流向分析。

主路徑：Grok（xAI API，OpenAI-compatible）。沒設 GROK_API_KEY 時 fallback 用簡單規則
拼一段繁中說明，前端會顯示 source badge 區分。
"""
from __future__ import annotations

import logging

from app.config import settings

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "你是台股 / 美股的資金流向分析師。請用繁體中文輸出，內容必須簡潔："
    "3 到 5 句重點，先說『近期資金動向是怎樣』，再說『可能的驅動因素』，"
    "最後提醒『要注意的風險或反訊號』。"
    "不要使用 markdown 標題或項目符號，直接用一段文字。"
    "不要回避，必要時用『偏多 / 偏空 / 觀望』作結論。"
    "禁止建議投資操作或暗示『買賣建議』，只描述資金行為與技術現象。"
)


def _summarize_payload(symbol: str, info: dict, flow: dict, ohlcv_summary: dict) -> str:
    """把所有資料壓成短字串餵給 LLM。"""
    lines: list[str] = []
    lines.append(f"標的：{info.get('name') or symbol}（{symbol}）")
    if info.get("sector"):
        lines.append(f"產業：{info.get('sector')} / {info.get('industry') or ''}")

    last_close = ohlcv_summary.get("last_close")
    pct_5d = ohlcv_summary.get("pct_5d")
    pct_20d = ohlcv_summary.get("pct_20d")
    pct_60d = ohlcv_summary.get("pct_60d")
    lines.append(
        f"最近收盤：{last_close}，近 5 日 {pct_5d}%、近 20 日 {pct_20d}%、近 60 日 {pct_60d}%。"
    )

    tw = flow.get("tw_institutional") or []
    if tw:
        last5 = tw[-5:]
        agg_foreign = sum((r["foreign"] or 0) for r in last5)
        agg_trust = sum((r["trust"] or 0) for r in last5)
        agg_dealer = sum((r["dealer"] or 0) for r in last5)
        lines.append(
            f"近 5 日三大法人合計（張）：外資 {agg_foreign:+.0f}、投信 {agg_trust:+.0f}、自營商 {agg_dealer:+.0f}。"
        )
        # 列最近 10 日明細
        detail = ", ".join(
            f"{r['date']} 外{r['foreign']:+.0f}/投{r['trust']:+.0f}/自{r['dealer']:+.0f}"
            for r in tw[-10:]
        )
        lines.append(f"最近 10 日：{detail}")

    insider = flow.get("us_insider") or []
    if insider:
        lines.append(f"內部人交易最近 {min(len(insider), 5)} 筆：")
        for r in insider[:5]:
            lines.append(
                f"  - {r.get('date')} {r.get('insider')} ({r.get('position')}) "
                f"{r.get('transaction')} 股數 {r.get('shares')} 金額 {r.get('value')}"
            )

    inst = flow.get("us_institutional") or []
    if inst:
        top3 = inst[:3]
        names = ", ".join(f"{h.get('holder')}（{h.get('pct_held')}）" for h in top3)
        lines.append(f"機構持股前三大：{names}")

    ind = flow.get("indicators") or []
    if ind:
        last = ind[-1]
        prev = ind[-2] if len(ind) >= 2 else None
        lines.append(
            f"技術面（最新）：MFI={last.get('mfi')}, OBV={last.get('obv')}, 量能z={last.get('vol_z')}"
        )
        if prev:
            lines.append(
                f"前一日：MFI={prev.get('mfi')}, OBV={prev.get('obv')}, 量能z={prev.get('vol_z')}"
            )

    return "\n".join(lines)


def _rule_based_summary(symbol: str, info: dict, flow: dict, ohlcv_summary: dict) -> str:
    """沒 API key 時用：依資金流向 + 技術指標拼接一段中文。"""
    name = info.get("name") or symbol
    pct_5d = ohlcv_summary.get("pct_5d")
    pct_20d = ohlcv_summary.get("pct_20d")

    parts: list[str] = []
    trend = "震盪"
    if isinstance(pct_20d, (int, float)):
        if pct_20d > 5:
            trend = "近 20 日呈現上行"
        elif pct_20d < -5:
            trend = "近 20 日呈現下行"
    parts.append(f"{name} 近期股價{trend}，近 5 日 {pct_5d}%、近 20 日 {pct_20d}%。")

    tw = flow.get("tw_institutional") or []
    if tw:
        last5 = tw[-5:]
        agg_foreign = sum((r["foreign"] or 0) for r in last5)
        agg_trust = sum((r["trust"] or 0) for r in last5)
        bias = "偏多" if (agg_foreign + agg_trust) > 0 else "偏空" if (agg_foreign + agg_trust) < 0 else "中性"
        parts.append(
            f"三大法人近 5 日合計外資 {agg_foreign:+.0f} 張、投信 {agg_trust:+.0f} 張，籌碼面{bias}。"
        )

    insider = flow.get("us_insider") or []
    if insider:
        buys = sum(1 for r in insider[:10] if str(r.get("transaction", "")).lower().find("buy") >= 0)
        sells = sum(1 for r in insider[:10] if str(r.get("transaction", "")).lower().find("sale") >= 0
                    or str(r.get("transaction", "")).lower().find("sell") >= 0)
        if buys or sells:
            parts.append(f"內部人最近 10 筆交易中買進 {buys} 筆、賣出 {sells} 筆。")

    ind = flow.get("indicators") or []
    if ind:
        last = ind[-1]
        mfi = last.get("mfi")
        vol_z = last.get("vol_z")
        notes: list[str] = []
        if isinstance(mfi, (int, float)):
            if mfi >= 80:
                notes.append(f"MFI {mfi:.1f} 已進入超買區")
            elif mfi <= 20:
                notes.append(f"MFI {mfi:.1f} 已進入超賣區")
            else:
                notes.append(f"MFI {mfi:.1f} 處於中性")
        if isinstance(vol_z, (int, float)) and abs(vol_z) >= 1.5:
            notes.append(f"成交量 z-score {vol_z:+.2f}（量能異常）")
        if notes:
            parts.append("技術面：" + "；".join(notes) + "。")

    parts.append("以上為規則式摘要，僅供參考；填入 GROK_API_KEY 後可改用 Grok 產出較深入的中文分析。")
    return " ".join(parts)


def _build_ohlcv_summary(indicators: list[dict]) -> dict:
    if not indicators:
        return {}
    closes = [r["close"] for r in indicators if r.get("close") is not None]
    if not closes:
        return {}
    last = closes[-1]

    def pct(n: int) -> float | None:
        if len(closes) <= n:
            return None
        prev = closes[-1 - n]
        if not prev:
            return None
        return round((last / prev - 1) * 100, 2)

    return {
        "last_close": round(last, 4),
        "pct_5d": pct(5),
        "pct_20d": pct(20),
        "pct_60d": pct(60),
    }


_ASK_SYSTEM_PROMPT = (
    "你是一位專業的股票研究助手，使用繁體中文回答關於上市公司的問題。"
    "回答要簡潔、具體、有資料佐證；如果使用者問的是『建議買進嗎 / 目標價多少』之類的投資建議，"
    "禮貌拒絕並改成提供事實面資訊（業務、產品、競爭、財務、近期事件），讓使用者自行判斷。"
    "如果你不確定某個事實，明確說『不確定』或『需要查證』，不要編造。"
    "不要使用 markdown 標題或大量條列，盡量用 3~5 句完整段落。"
)


def ask_about_stock(
    symbol: str,
    question: str,
    info: dict,
    history: list[dict] | None = None,
) -> dict:
    """讓使用者對特定股票問問題。回 {answer, source, model?}.

    history: 之前的 [{role, content}, ...]，會接到 prompt 之前。
    """
    api_key = settings.grok_api_key.strip()
    if not api_key:
        return {
            "answer": (
                "尚未設定 GROK_API_KEY，無法提供 AI 問答。"
                "請在 backend/.env 填入後重啟即可使用此功能。"
            ),
            "source": "rule",
        }

    model = settings.grok_model.strip() or "grok-4"

    # 把 info 壓縮成幾行 context，避免一次塞太多 token
    ctx_lines = [f"標的：{info.get('name') or symbol}（{symbol}）"]
    if info.get("sector"):
        ctx_lines.append(f"產業：{info.get('sector')} / {info.get('industry') or ''}")
    if info.get("market_cap"):
        ctx_lines.append(f"市值：{info.get('market_cap')}")
    if info.get("country"):
        ctx_lines.append(f"國家：{info.get('country')}")
    if info.get("website"):
        ctx_lines.append(f"網站：{info.get('website')}")
    if info.get("summary"):
        # 公司簡介本身就放進 context，使用者可以直接問問題
        ctx_lines.append("公司簡介（資料源 yfinance）：")
        ctx_lines.append(str(info["summary"])[:2000])
    context = "\n".join(ctx_lines)

    messages: list[dict] = [
        {"role": "system", "content": _ASK_SYSTEM_PROMPT},
        {"role": "system", "content": f"以下是關於這檔股票的背景資料：\n{context}"},
    ]
    if history:
        for h in history[-6:]:  # 最多保留前 6 輪
            role = h.get("role")
            content = h.get("content")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": question})

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1", timeout=60.0)
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.5,
        )
        text = (resp.choices[0].message.content or "").strip()
        if not text:
            raise RuntimeError("empty response from Grok")
        return {"answer": text, "source": "grok", "model": model}
    except Exception as e:
        logger.warning("Grok ask_about_stock failed: %s", e)
        return {
            "answer": f"Grok 呼叫失敗：{type(e).__name__} - {e}",
            "source": "error",
        }


def analyze_fund_flow(symbol: str, flow: dict, info: dict) -> dict:
    """回傳 {analysis: str, source: 'grok'|'rule', model?: str}"""
    ohlcv_summary = _build_ohlcv_summary(flow.get("indicators") or [])

    api_key = settings.grok_api_key.strip()
    model = settings.grok_model.strip() or "grok-4"

    if not api_key:
        text = _rule_based_summary(symbol, info, flow, ohlcv_summary)
        return {"analysis": text, "source": "rule"}

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1", timeout=30.0)
        user_msg = _summarize_payload(symbol, info, flow, ohlcv_summary)
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.4,
        )
        text = (resp.choices[0].message.content or "").strip()
        if not text:
            raise RuntimeError("empty response from Grok")
        return {"analysis": text, "source": "grok", "model": model}
    except Exception as e:
        logger.warning("Grok call failed, fallback to rule: %s", e)
        text = _rule_based_summary(symbol, info, flow, ohlcv_summary)
        return {
            "analysis": text + f"（Grok 呼叫失敗：{type(e).__name__}）",
            "source": "rule",
        }
