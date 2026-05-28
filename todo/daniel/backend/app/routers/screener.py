from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.data import universe
from app.db import get_db
from app.models.schemas import ScreenerRequest
from app.services import screener_service

router = APIRouter()


@router.get("/universe")
def list_universe(market: str = "ALL", db: Session = Depends(get_db)) -> dict:
    syms = universe.all_symbols(db, market)
    return {"market": market.upper(), "symbols": syms, "count": len(syms)}


@router.post("/run")
def run_screener(req: ScreenerRequest, db: Session = Depends(get_db)) -> dict:
    if req.symbols:
        symbols = req.symbols
    else:
        # 全市場直接拿太多會打爆 yfinance，預設限縮 Top 200
        symbols = universe.top_n(db, 200, req.market)

    cond = req.conditions.model_dump() if req.conditions else {}
    results = screener_service.run(symbols, cond, limit=req.limit)
    return {
        "total": len(results),
        "scanned": len(symbols),
        "results": results,
    }
