"""AI 選股：熱門題材 + 候選股推演（Grok reasoning + live search）。"""
from __future__ import annotations

from fastapi import APIRouter, Query

from app.services import ai_picks_service

router = APIRouter()


@router.get("")
def get_ai_picks(
    refresh: bool = Query(False, description="略過 24h 快取重新呼叫 LLM"),
    top_n: int = Query(10, ge=1, le=20, description="想要回傳幾個題材"),
    theme_hint: str = Query(
        "",
        description="使用者指定的題材關鍵字，例如『AI 伺服器、低軌道衛星』；留空表示讓模型自由選題",
    ),
) -> dict:
    return ai_picks_service.generate(
        refresh=refresh, top_n=top_n, theme_hint=theme_hint.strip()
    )
