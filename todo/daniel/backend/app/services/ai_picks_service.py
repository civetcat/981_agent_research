"""AI 選股：用 Grok reasoning model 推演當前熱門題材 + 候選股。

設計要點：
- Reasoning 模型 (grok-4) 慢且貴 → 24 小時檔案快取，按下「重新分析」才會強制重跑
- 開啟 xAI live search（search_parameters via extra_body），讓模型抓最新題材
- 要求 JSON 輸出，方便前端結構化顯示
- 沒設 GROK_API_KEY 時直接回 {error: ...}，不做規則式 fallback（沒網路 + 沒 LLM 給不出有意義的「熱門題材」）
"""
from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

_CACHE_TTL_SEC = 24 * 3600

_SCHEMA_BLOCK = (
    "JSON schema："
    "{"
    '  "as_of_date": "YYYY-MM-DD（你做出此分析的日期）",'
    '  "themes": ['
    "    {"
    '      "name": "題材名稱（短，6 字以內）",'
    '      "category": "AI / 半導體 / 電動車 / 軍工 / 高股息 / 重電 / 生技 / 加密 / 其他 — 擇一",'
    '      "heat_level": "high / medium / low — 目前熱度",'
    '      "summary": "為什麼這題材正在發酵（2~4 句，引用具體事件 / 數據 / 政策 / 法人動向）",'
    '      "drivers": ["列出 3~5 個關鍵驅動因素"],'
    '      "stocks": ['
    "        {"
    '          "symbol": "台股請用 2330.TW 形式，美股直接用代號，例如 NVDA",'
    '          "name": "公司中文名（台股）或英文名（美股）",'
    '          "thesis": "這檔為什麼可能成為下一個熱門股（2~3 句具體分析）",'
    '          "risks": "1 句最大風險或反訊號"'
    "        }"
    "      ]"
    "    }"
    "  ]"
    "}"
)


def _build_prompts(top_n: int, theme_hint: str) -> tuple[str, str]:
    """根據使用者輸入動態組 prompt。"""
    n = max(1, min(20, top_n))

    if theme_hint:
        # 使用者指定了題材方向 → 圍繞該方向推演子題材
        system = (
            "你是一位資深的股市題材分析師，專精於台股與美股。"
            "你的任務是針對使用者指定的題材方向，用最新的新聞與市場資訊，"
            f"推演『正在發酵 / 接下來幾週可能成為熱門』的 **{n} 個子題材或角度**，"
            "並針對每個題材列出 2~4 檔最直接受惠的台股或美股，並說明為什麼這檔可能成為下一個熱門股。"
            "務必使用繁體中文。回覆必須是有效的 JSON，不要包覆 markdown 程式碼框。"
            f"{_SCHEMA_BLOCK}"
            f"重要：必須列出 **正好 {n} 個題材**，依目前熱度與發酵潛力由高到低排序。"
            "題材彼此之間需具有差異性，不要重複或把同一概念拆兩次。"
            "每個題材底下 2~4 檔；總計約 "
            f"{n * 2}~{n * 4} 檔。"
            "只列流動性夠好的中大型股或主流 ETF，不要列冷門小型股。"
            "禁止編造不存在的股票代號。沒把握的代號就不列。"
            "禁止給投資建議或目標價，只描述題材與標的之間的關係。"
        )
        user = (
            f"使用者指定的題材方向：「{theme_hint}」。"
            f"請圍繞這個方向，根據最新一週的新聞、財報、政策、法人動向，"
            f"推演 Top {n} 個最具發酵潛力的子題材或細分角度（依熱度排序，最熱在前），"
            "並列出每個題材底下最直接受惠的 2~4 檔標的。"
            "請按照系統訊息中的 JSON schema 回覆。"
        )
    else:
        # 沒指定 → 自由選題，多樣化
        system = (
            "你是一位資深的股市題材分析師，專精於台股與美股。"
            "你的任務是用最新的新聞與市場資訊，推演『目前正在發酵 / 接下來幾週可能成為熱門』的題材，"
            "並針對每個題材列出 2~4 檔最直接受惠的台股或美股，並說明為什麼這檔可能成為下一個熱門股。"
            "務必使用繁體中文。回覆必須是有效的 JSON，不要包覆 markdown 程式碼框。"
            f"{_SCHEMA_BLOCK}"
            f"重要：必須列出 **正好 {n} 個題材**（top {n}），依目前熱度與發酵潛力由高到低排序。"
            "題材彼此之間需具有差異性，不要把同一個概念拆成兩個（例如 AI 伺服器與 AI 晶片不要分開）。"
            f"至少要混合 {min(3, n)} 個以上的不同 category，避免全部集中在 AI / 半導體。"
            "每個題材底下 2~4 檔；總計約 "
            f"{n * 2}~{n * 4} 檔。"
            "只列流動性夠好的中大型股或主流 ETF，不要列冷門小型股。"
            "禁止編造不存在的股票代號。沒把握的代號就不列。"
            "禁止給投資建議或目標價，只描述題材與標的之間的關係。"
        )
        user = (
            "請根據最新一週的新聞、財報、政策、法人動向，"
            f"推演目前正在發酵的台股 / 美股題材 Top {n}（依熱度與潛力排序，最熱在前），"
            "題材必須涵蓋多個 category（不要全部都是 AI / 半導體），"
            "並列出每個題材底下最直接受惠的 2~4 檔標的。"
            "請按照系統訊息中的 JSON schema 回覆。"
        )
    return system, user


def _cache_path(top_n: int = 10, theme_hint: str = "") -> Path:
    """每組（top_n, theme_hint）一個獨立檔；無 hint 仍用 latest.json 維持相容。"""
    import hashlib

    p = settings.cache_path / "ai_picks"
    p.mkdir(parents=True, exist_ok=True)
    if not theme_hint and top_n == 10:
        return p / "latest.json"
    if theme_hint:
        # 把題材 hint hash 成短字串避免檔名裡有奇怪字元
        h = hashlib.sha1(theme_hint.encode("utf-8")).hexdigest()[:10]
        return p / f"top{top_n}_{h}.json"
    return p / f"top{top_n}.json"


def _read_cache(top_n: int = 10, theme_hint: str = "") -> dict | None:
    p = _cache_path(top_n, theme_hint)
    if not p.exists():
        return None
    try:
        if (time.time() - p.stat().st_mtime) > _CACHE_TTL_SEC:
            return None
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        logger.debug("ai picks cache read failed: %s", e)
        return None


def _write_cache(data: dict, top_n: int = 10, theme_hint: str = "") -> None:
    try:
        _cache_path(top_n, theme_hint).write_text(
            json.dumps(data, ensure_ascii=False), encoding="utf-8"
        )
    except Exception as e:
        logger.debug("ai picks cache write failed: %s", e)


def _extract_json(text: str) -> dict | None:
    """容錯地從 LLM 回覆抽出 JSON。reasoning 模型偶爾還是會包 markdown 框。"""
    if not text:
        return None
    text = text.strip()

    # 去除 markdown 程式碼框
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)

    # 找第一個 { 到最後一個 }
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except Exception as e:
        logger.warning("ai picks json parse failed: %s", e)
        return None


def generate(
    refresh: bool = False, top_n: int = 10, theme_hint: str = ""
) -> dict:
    """回傳 {as_of_date, themes, source, model, ...} 或 {error}."""
    top_n = max(1, min(20, top_n))
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
            "error": "未設定 GROK_API_KEY。AI 選股需要 LLM 推演，請在 backend/.env 填入後重啟。",
            "themes": [],
        }

    model = settings.grok_model.strip() or "grok-4"
    system_prompt, user_prompt = _build_prompts(top_n, theme_hint)

    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=api_key, base_url="https://api.x.ai/v1", timeout=600.0
        )

        # 用 xAI Responses API + 內建 web_search tool。
        # （chat.completions 不再支援新版 server-side tools；舊的 search_parameters 已 410 deprecated）
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
            # fallback：不開 web search，純 reasoning（題材會偏舊）
            resp = client.responses.create(
                model=model,
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )

        # 從 response.output 抽出 assistant 最終 message 的 output_text
        raw = ""
        try:
            # SDK 1.50+ 有 output_text 便利屬性
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

        # 模型偶爾會多給/少給，強制裁切到使用者指定的數量
        themes = parsed.get("themes") or []
        if len(themes) > top_n:
            themes = themes[:top_n]
        parsed["themes"] = themes

        # 從 web_search 工具呼叫的結果抽 citations（URLs）
        citations: list[str] = []
        try:
            for item in getattr(resp, "output", []) or []:
                if getattr(item, "type", None) != "message":
                    continue
                for c in getattr(item, "content", []) or []:
                    for ann in getattr(c, "annotations", []) or []:
                        url = (
                            getattr(ann, "url", None)
                            or (isinstance(ann, dict) and ann.get("url"))
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
        logger.exception("ai picks generation failed")
        return {
            "error": f"Grok 呼叫失敗：{type(e).__name__} - {e}",
            "themes": [],
        }
