"""AI 推薦 ETF：用 Grok reasoning + 即時搜尋推演當前最值得關注的 ETF 主題。

設計與 ai_picks_service 同型：
- 24 小時檔案快取，路徑 backend/data_cache/ai_etf_picks/
- 多桶 cache：latest.json / top{N}.json / top{N}_{hash}.json
- 沒設 GROK_API_KEY 直接回 {error}
- 把 etf_list.py 的白名單放進 system prompt，要求模型優先從中挑（避免幻覺代號）
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from pathlib import Path

from app.config import settings
from app.data.etf_list import all_etfs

logger = logging.getLogger(__name__)

_CACHE_TTL_SEC = 24 * 3600

_SCHEMA_BLOCK = (
    "JSON schema："
    "{"
    '  "as_of_date": "YYYY-MM-DD（你做出此分析的日期）",'
    '  "themes": ['
    "    {"
    '      "name": "主題名稱（短，10 字以內，例如：高股息、AI、半導體、長天期美債、黃金）",'
    '      "category": "市值型 / 高股息 / 產業主題 / 債券 / REITs黃金商品 / 海外區域 / 其他 — 擇一",'
    '      "heat_level": "high / medium / low — 目前熱度",'
    '      "summary": "為什麼此主題現在值得關注（2~4 句，引用具體事件 / 政策 / 利率 / 資金流向）",'
    '      "drivers": ["列出 3~5 個關鍵驅動因素"],'
    '      "etfs": ['
    "        {"
    '          "symbol": "台股 ETF 用 0050.TW 形式，美股 ETF 直接用代號，例如 SPY",'
    '          "name": "ETF 中文名（台股）或英文名（美股）",'
    '          "expense_ratio_hint": "費用率提示，例如 0.30% 或 留空",'
    '          "thesis": "為什麼這檔 ETF 是該主題的好代表（2~3 句）",'
    '          "risks": "1 句最大風險",'
    '          "off_whitelist": false'
    "        }"
    "      ]"
    "    }"
    "  ]"
    "}"
)


def _build_whitelist_block() -> str:
    """組出白名單字串，分台股 / 美股兩段，給 LLM 當挑選清單。"""
    tw_lines: list[str] = []
    us_lines: list[str] = []
    for sym, name, _cat, market in all_etfs():
        line = f"{sym} {name}"
        if market == "TW":
            tw_lines.append(line)
        else:
            us_lines.append(line)
    return (
        "以下為白名單 ETF（流動性 / 知名度足夠，請優先從這裡挑）：\n"
        "【台股 ETF】\n" + "; ".join(tw_lines) + "\n"
        "【美股 ETF】\n" + "; ".join(us_lines) + "\n"
        "規則：每個主題下推薦的 ETF 至少 80% 必須來自上方白名單；"
        "若白名單外確實有受惠且流動性夠的 ETF 可補充，但必須將該檔的 off_whitelist 設為 true。"
        "禁止編造不存在的 ETF 代號。沒把握就只列白名單。"
    )


def _build_prompts(top_n: int, theme_hint: str) -> tuple[str, str]:
    n = max(1, min(15, top_n))
    whitelist = _build_whitelist_block()

    if theme_hint:
        system = (
            "你是一位資深的 ETF 投資顧問，專精於台股與美股 ETF 配置。"
            "你的任務是針對使用者指定的方向，用最新的市場資訊，"
            f"推演 **{n} 個最值得關注的 ETF 子主題**，"
            "並針對每個主題列出 2~4 檔最具代表性的 ETF + 為什麼。"
            "務必使用繁體中文。回覆必須是有效的 JSON，不要包覆 markdown 程式碼框。"
            f"{_SCHEMA_BLOCK}"
            f"{whitelist}"
            f"重要：必須列出 **正好 {n} 個主題**，依目前關注度由高到低排序，主題彼此差異化。"
            "只列流動性夠好的主流 ETF。禁止給投資建議或目標價。"
        )
        user = (
            f"使用者指定的方向：「{theme_hint}」。"
            f"請圍繞這個方向，根據最新市場資訊推演 Top {n} 個值得關注的 ETF 子主題，"
            "每個主題下列 2~4 檔具體 ETF。請按照系統訊息中的 JSON schema 回覆。"
        )
    else:
        system = (
            "你是一位資深的 ETF 投資顧問，專精於台股與美股 ETF 配置。"
            "你的任務是用最新的市場資訊，推演『目前最值得關注』的 ETF 主題，"
            "涵蓋面向例如：高股息、AI / 半導體、長天期 / 短天期債券、原物料 / 黃金、市場大盤 ETF、海外區域等，"
            "並針對每個主題列出 2~4 檔最具代表性的 ETF + 為什麼。"
            "務必使用繁體中文。回覆必須是有效的 JSON，不要包覆 markdown 程式碼框。"
            f"{_SCHEMA_BLOCK}"
            f"{whitelist}"
            f"重要：必須列出 **正好 {n} 個主題**（top {n}），依關注度由高到低排序。"
            f"至少要混合 {min(4, n)} 個以上不同 category（不要全部集中在 AI / 半導體）。"
            "每個主題底下 2~4 檔具體 ETF；只列流動性夠好的主流 ETF；禁止給投資建議或目標價。"
        )
        user = (
            "請根據最新一週的新聞、政策、利率動向、資金流，"
            f"推演目前最值得關注的台股 / 美股 ETF 主題 Top {n}（依關注度排序），"
            "主題需涵蓋多個 category，並列出每主題下 2~4 檔具體 ETF。"
            "請按照系統訊息中的 JSON schema 回覆。"
        )
    return system, user


def _cache_path(top_n: int = 8, theme_hint: str = "") -> Path:
    p = settings.cache_path / "ai_etf_picks"
    p.mkdir(parents=True, exist_ok=True)
    if not theme_hint and top_n == 8:
        return p / "latest.json"
    if theme_hint:
        h = hashlib.sha1(theme_hint.encode("utf-8")).hexdigest()[:10]
        return p / f"top{top_n}_{h}.json"
    return p / f"top{top_n}.json"


def _read_cache(top_n: int, theme_hint: str) -> dict | None:
    p = _cache_path(top_n, theme_hint)
    if not p.exists():
        return None
    try:
        if (time.time() - p.stat().st_mtime) > _CACHE_TTL_SEC:
            return None
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        logger.debug("ai etf picks cache read failed: %s", e)
        return None


def _write_cache(data: dict, top_n: int, theme_hint: str) -> None:
    try:
        _cache_path(top_n, theme_hint).write_text(
            json.dumps(data, ensure_ascii=False), encoding="utf-8"
        )
    except Exception as e:
        logger.debug("ai etf picks cache write failed: %s", e)


def _extract_json(text: str) -> dict | None:
    if not text:
        return None
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except Exception as e:
        logger.warning("ai etf picks json parse failed: %s", e)
        return None


def generate(
    refresh: bool = False, top_n: int = 8, theme_hint: str = ""
) -> dict:
    top_n = max(1, min(15, top_n))
    theme_hint = (theme_hint or "").strip()

    if not refresh:
        cached = _read_cache(top_n, theme_hint)
        if cached is not None:
            return {
                **cached,
                "from_cache": True,
                "top_n": top_n,
                "theme_hint": theme_hint,
            }

    api_key = settings.grok_api_key.strip()
    if not api_key:
        return {
            "error": "未設定 GROK_API_KEY。AI 推薦 ETF 需要 LLM 推演，請在 backend/.env 填入後重啟。",
            "themes": [],
        }

    model = settings.grok_model.strip() or "grok-4"
    system_prompt, user_prompt = _build_prompts(top_n, theme_hint)

    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=api_key, base_url="https://api.x.ai/v1", timeout=600.0
        )

        web_search_used = True
        try:
            resp = client.responses.create(
                model=model,
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                tools=[{"type": "web_search"}],
            )
        except Exception as e:
            logger.warning("Responses API with web_search failed: %s", e)
            web_search_used = False
            resp = client.responses.create(
                model=model,
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )

        raw = ""
        try:
            raw = getattr(resp, "output_text", "") or ""
        except Exception:
            raw = ""
        if not raw:
            for item in getattr(resp, "output", []) or []:
                if getattr(item, "type", None) != "message":
                    continue
                for c in getattr(item, "content", []) or []:
                    if getattr(c, "type", None) == "output_text":
                        raw = getattr(c, "text", "") or ""
                        break
                if raw:
                    break

        parsed = _extract_json(raw)
        if not parsed or not isinstance(parsed.get("themes"), list):
            return {
                "error": "LLM 回覆解析失敗",
                "raw_excerpt": raw[:500],
                "themes": [],
            }

        themes = parsed.get("themes") or []
        if len(themes) > top_n:
            themes = themes[:top_n]
        parsed["themes"] = themes

        citations: list[str] = []
        try:
            for item in getattr(resp, "output", []) or []:
                if getattr(item, "type", None) != "message":
                    continue
                for c in getattr(item, "content", []) or []:
                    for ann in getattr(c, "annotations", []) or []:
                        url = getattr(ann, "url", None) or (
                            isinstance(ann, dict) and ann.get("url")
                        )
                        if url and url not in citations:
                            citations.append(url)
        except Exception:
            pass

        result = {
            **parsed,
            "source": "grok",
            "model": model,
            "citations": citations,
            "web_search_used": web_search_used,
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "top_n": top_n,
            "theme_hint": theme_hint,
        }
        _write_cache(result, top_n, theme_hint)
        return {**result, "from_cache": False}

    except Exception as e:
        logger.exception("ai etf picks generation failed")
        return {
            "error": f"Grok 呼叫失敗：{type(e).__name__} - {e}",
            "themes": [],
        }
