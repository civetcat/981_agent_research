from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.session import get_current_user
from app.db import get_db
from app.models.schemas import CashFlowRequest, PortfolioResetRequest, TransactionRequest
from app.models import db as orm
from app.services import portfolio_service

router = APIRouter()


@router.get("")
def get_portfolio(
    db: Session = Depends(get_db), current_user: orm.User = Depends(get_current_user)
) -> dict:
    return portfolio_service.get_state(db, current_user.id)


@router.get("/summary")
def get_portfolio_summary(
    db: Session = Depends(get_db), current_user: orm.User = Depends(get_current_user)
) -> dict:
    return portfolio_service.get_summary(db, current_user.id)


@router.post("/transactions")
def add_transaction(
    req: TransactionRequest,
    db: Session = Depends(get_db),
    current_user: orm.User = Depends(get_current_user),
) -> dict:
    try:
        return portfolio_service.transact(
            db,
            symbol=req.symbol,
            side=req.side,
            qty=req.qty,
            price=req.price,
            note=req.note,
            user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/deposit")
def deposit(
    req: CashFlowRequest,
    db: Session = Depends(get_db),
    current_user: orm.User = Depends(get_current_user),
) -> dict:
    try:
        return portfolio_service.deposit(db, req.amount, req.note, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/withdraw")
def withdraw(
    req: CashFlowRequest,
    db: Session = Depends(get_db),
    current_user: orm.User = Depends(get_current_user),
) -> dict:
    try:
        return portfolio_service.withdraw(db, req.amount, req.note, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/reset")
def reset_portfolio(
    req: PortfolioResetRequest,
    db: Session = Depends(get_db),
    current_user: orm.User = Depends(get_current_user),
) -> dict:
    p = portfolio_service.reset(db, initial_cash=req.initial_cash, user_id=current_user.id)
    return {
        "id": p.id,
        "initial_cash": p.initial_cash,
        "total_invested": p.total_invested,
        "cash": p.cash,
    }
