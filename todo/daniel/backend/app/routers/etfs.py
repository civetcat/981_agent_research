"""ETF 排行 API。"""
from __future__ import annotations

from fastapi import APIRouter, Query

from app.services import etf_service

router = APIRouter()


@router.get("/categories")
def get_categories() -> list[dict]:
    return etf_service.categories()


@router.get("/ranking")
def ranking(
    market: str | None = Query(None, description="TW / US / 留空表示全部"),
    category: str | None = Query(None),
) -> dict:
    items = etf_service.list_etfs(market=market, category=category)
    return {"count": len(items), "items": items}
