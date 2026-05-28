"""推薦評分儀表板 API。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.services import verdict_service

router = APIRouter()


@router.get("/{symbol}")
def get_verdict(
    symbol: str,
    entry_mode: str = Query("balanced", description="conservative / balanced / aggressive / sma_pullback"),
) -> dict:
    try:
        return verdict_service.evaluate(symbol, entry_mode=entry_mode)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
