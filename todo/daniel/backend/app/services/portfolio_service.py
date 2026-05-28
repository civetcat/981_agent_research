"""投資組合服務：聚合交易紀錄計算持倉、即時報價、權益、績效。

交易種類：
- BUY / SELL：股票買賣（會動到 cash 與持倉）
- DEPOSIT / WITHDRAW：入金 / 出金（只動 cash 與 total_invested）
"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime

from sqlalchemy.orm import Session

from app.data import fetcher
from app.models import db as orm

logger = logging.getLogger(__name__)


def _last_price(symbol: str) -> float | None:
    try:
        df = fetcher.get_ohlcv(symbol, period="1mo")
        if df is None or df.empty:
            return None
        return float(df["close"].iloc[-1])
    except Exception as e:
        logger.warning("price fetch failed for %s: %s", symbol, e)
        return None


def get_default(db: Session, user_id: int = 1) -> orm.Portfolio:
    p = (
        db.query(orm.Portfolio)
        .filter(orm.Portfolio.user_id == user_id)
        .order_by(orm.Portfolio.id)
        .first()
    )
    if p is None:
        kwargs = {
            "user_id": user_id,
            "name": "My Portfolio",
            "initial_cash": 1_000_000.0,
            "total_invested": 1_000_000.0,
            "cash": 1_000_000.0,
        }
        if user_id == 1:
            kwargs["id"] = 1
        p = orm.Portfolio(**kwargs)
        db.add(p)
        db.commit()
        db.refresh(p)
    return p


def reset(db: Session, initial_cash: float = 1_000_000.0, user_id: int = 1) -> orm.Portfolio:
    p = get_default(db, user_id)
    db.query(orm.Transaction).filter(orm.Transaction.portfolio_id == p.id).delete()
    p.initial_cash = initial_cash
    p.total_invested = initial_cash
    p.cash = initial_cash
    db.commit()
    db.refresh(p)
    return p


def deposit(db: Session, amount: float, note: str | None = None, user_id: int = 1) -> dict:
    if amount <= 0:
        raise ValueError("amount must be > 0")
    p = get_default(db, user_id)
    p.cash += amount
    p.total_invested += amount
    tx = orm.Transaction(
        portfolio_id=p.id,
        symbol="CASH",
        side="DEPOSIT",
        qty=amount,
        price=1.0,
        fee=0.0,
        note=note,
        executed_at=datetime.utcnow(),
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return {
        "id": tx.id,
        "side": "DEPOSIT",
        "amount": amount,
        "cash_after": round(p.cash, 2),
        "total_invested": round(p.total_invested, 2),
    }


def withdraw(db: Session, amount: float, note: str | None = None, user_id: int = 1) -> dict:
    if amount <= 0:
        raise ValueError("amount must be > 0")
    p = get_default(db, user_id)
    if amount > p.cash + 1e-6:
        raise ValueError(f"insufficient cash: have {p.cash:.2f}, withdraw {amount:.2f}")
    p.cash -= amount
    p.total_invested = max(0.0, p.total_invested - amount)
    tx = orm.Transaction(
        portfolio_id=p.id,
        symbol="CASH",
        side="WITHDRAW",
        qty=amount,
        price=1.0,
        fee=0.0,
        note=note,
        executed_at=datetime.utcnow(),
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return {
        "id": tx.id,
        "side": "WITHDRAW",
        "amount": amount,
        "cash_after": round(p.cash, 2),
        "total_invested": round(p.total_invested, 2),
    }


def transact(
    db: Session,
    symbol: str,
    side: str,
    qty: float,
    price: float | None = None,
    fee_rate: float = 0.001425,
    note: str | None = None,
    user_id: int = 1,
) -> dict:
    side = side.upper()
    if side not in ("BUY", "SELL"):
        raise ValueError("side must be BUY or SELL")
    if qty <= 0:
        raise ValueError("qty must be > 0")

    symbol = fetcher.normalize_symbol(symbol)
    if price is None:
        p = _last_price(symbol)
        if p is None:
            raise ValueError(f"cannot fetch price for {symbol}")
        price = p

    fee = qty * price * fee_rate
    portfolio = get_default(db, user_id)

    if side == "BUY":
        cost = qty * price + fee
        if cost > portfolio.cash + 1e-6:
            raise ValueError(f"insufficient cash: need {cost:.2f}, have {portfolio.cash:.2f}")
        portfolio.cash -= cost
    else:
        position = _position_for(db, portfolio.id, symbol)
        if position["qty"] < qty - 1e-6:
            raise ValueError(f"insufficient position: hold {position['qty']}, sell {qty}")
        proceeds = qty * price - fee
        portfolio.cash += proceeds

    tx = orm.Transaction(
        portfolio_id=portfolio.id,
        symbol=symbol,
        side=side,
        qty=qty,
        price=price,
        fee=fee,
        note=note,
        executed_at=datetime.utcnow(),
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)

    return {
        "id": tx.id,
        "symbol": tx.symbol,
        "side": tx.side,
        "qty": tx.qty,
        "price": tx.price,
        "fee": tx.fee,
        "executed_at": tx.executed_at.isoformat(),
        "note": tx.note,
    }


def _position_for(db: Session, portfolio_id: int, symbol: str) -> dict:
    txs = (
        db.query(orm.Transaction)
        .filter(
            orm.Transaction.portfolio_id == portfolio_id,
            orm.Transaction.symbol == symbol,
            orm.Transaction.side.in_(("BUY", "SELL")),
        )
        .order_by(orm.Transaction.executed_at)
        .all()
    )
    qty = 0.0
    cost_basis = 0.0
    realized = 0.0
    for t in txs:
        if t.side == "BUY":
            cost_basis = (cost_basis * qty + t.qty * t.price + t.fee) / max(qty + t.qty, 1e-12)
            qty += t.qty
        else:
            realized += (t.price - cost_basis) * t.qty - t.fee
            qty -= t.qty
    return {"symbol": symbol, "qty": qty, "avg_cost": cost_basis, "realized_pnl": realized}


def get_state(db: Session, user_id: int = 1) -> dict:
    p = get_default(db, user_id)
    txs = (
        db.query(orm.Transaction)
        .filter(orm.Transaction.portfolio_id == p.id)
        .order_by(orm.Transaction.executed_at)
        .all()
    )

    grouped: dict[str, list[orm.Transaction]] = defaultdict(list)
    for t in txs:
        if t.side in ("BUY", "SELL"):
            grouped[t.symbol].append(t)

    positions = []
    total_market_value = 0.0
    total_cost = 0.0
    total_realized = 0.0

    for sym, lst in grouped.items():
        qty = 0.0
        cost = 0.0
        realized = 0.0
        for t in lst:
            if t.side == "BUY":
                cost = (cost * qty + t.qty * t.price + t.fee) / max(qty + t.qty, 1e-12)
                qty += t.qty
            else:
                realized += (t.price - cost) * t.qty - t.fee
                qty -= t.qty
        total_realized += realized
        if qty > 1e-9:
            last = _last_price(sym)
            mkt = (last or cost) * qty
            unreal = (last - cost) * qty if last is not None else 0.0
            total_market_value += mkt
            total_cost += cost * qty
            positions.append(
                {
                    "symbol": sym,
                    "qty": round(qty, 6),
                    "avg_cost": round(cost, 4),
                    "last_price": last,
                    "market_value": round(mkt, 2),
                    "unrealized_pnl": round(unreal, 2),
                    "unrealized_pct": round((last / cost - 1) * 100, 2) if last and cost else None,
                    "weight": None,
                }
            )

    total_equity = p.cash + total_market_value
    for pos in positions:
        pos["weight"] = round(pos["market_value"] / total_equity * 100, 2) if total_equity else 0.0

    base = p.total_invested if p.total_invested else p.initial_cash
    total_return_pct = (total_equity / base - 1) * 100 if base else 0.0

    history = [
        {
            "id": t.id,
            "symbol": t.symbol,
            "side": t.side,
            "qty": t.qty,
            "price": t.price,
            "fee": t.fee,
            "note": t.note,
            "executed_at": t.executed_at.isoformat(),
        }
        for t in reversed(txs)
    ]

    return {
        "id": p.id,
        "name": p.name,
        "initial_cash": p.initial_cash,
        "total_invested": round(p.total_invested, 2),
        "cash": round(p.cash, 2),
        "market_value": round(total_market_value, 2),
        "total_equity": round(total_equity, 2),
        "total_cost": round(total_cost, 2),
        "unrealized_pnl": round(total_market_value - total_cost, 2),
        "realized_pnl": round(total_realized, 2),
        "total_return_pct": round(total_return_pct, 2),
        "positions": positions,
        "transactions": history,
    }


def get_summary(db: Session, user_id: int = 1) -> dict:
    """精簡版（給 navbar 徽章用）。"""
    s = get_state(db, user_id)
    return {
        "cash": s["cash"],
        "market_value": s["market_value"],
        "total_equity": s["total_equity"],
        "total_invested": s["total_invested"],
        "total_return_pct": s["total_return_pct"],
        "positions_count": len(s["positions"]),
    }
