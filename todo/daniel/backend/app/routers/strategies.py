from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.strategies import catalog

router = APIRouter()


@router.get("/catalog")
def get_catalog(category: str | None = None) -> dict:
    return {
        "categories": [
            {"key": k, "label": v} for k, v in catalog.CATEGORY_LABEL.items()
        ],
        "items": catalog.list_catalog(category),
        "scenarios": catalog.SCENARIOS,
    }


@router.get("/{key}")
def get_strategy(key: str) -> dict:
    s = catalog.get_by_key(key)
    if s is None:
        raise HTTPException(status_code=404, detail="strategy not found")
    return s
