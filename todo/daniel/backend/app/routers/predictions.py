"""策略預測 API。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.services import prediction_service

router = APIRouter()


@router.get("/{symbol}")
def predict_for_stock(symbol: str) -> dict:
    try:
        return prediction_service.for_stock(symbol)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
