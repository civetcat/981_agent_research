"""AI 推薦 ETF：值得關注的 ETF 主題 + 候選 ETF（Grok reasoning + live search）。"""
from __future__ import annotations

from fastapi import APIRouter, Query

from app.services import ai_etf_picks_service

router = APIRouter()


@router.get("")
def get_ai_etf_picks(
    refresh: bool = Query(False, description="略過 24h 快取重新呼叫 LLM"),
    top_n: int = Query(8, ge=1, le=15, description="想要回傳幾個 ETF 主題"),
    theme_hint: str = Query(
        "",
        description="使用者指定的方向關鍵字，例如『高股息、長天期美債』；留空表示讓模型自由選題",
    ),
) -> dict:
    return ai_etf_picks_service.generate(
        refresh=refresh, top_n=top_n, theme_hint=theme_hint.strip()
    )
