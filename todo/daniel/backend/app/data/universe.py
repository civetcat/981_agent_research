"""股票池查詢：從 DB 讀取（fallback 到內建 Top 清單）。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.data import listings
from app.models import db as orm


def all_symbols(db: Session, market: str = "ALL") -> list[str]:
    q = db.query(orm.Stock.symbol)
    if market.upper() != "ALL":
        q = q.filter(orm.Stock.market == market.upper())
    rows = q.order_by(orm.Stock.liquidity_rank.asc()).all()
    if rows:
        return [r[0] for r in rows]
    # fallback：DB 還沒灌
    if market.upper() == "TW":
        return [s for s, _ in listings.TW_TOP]
    if market.upper() == "US":
        return [s for s, _ in listings.US_TOP]
    return [s for s, _ in listings.TW_TOP] + [s for s, _ in listings.US_TOP]


def top_n(db: Session, n: int, market: str = "ALL") -> list[str]:
    q = db.query(orm.Stock.symbol)
    if market.upper() != "ALL":
        q = q.filter(orm.Stock.market == market.upper())
    rows = q.order_by(orm.Stock.liquidity_rank.asc()).limit(n).all()
    if rows:
        return [r[0] for r in rows]
    fallback = [s for s, _ in listings.TW_TOP] + [s for s, _ in listings.US_TOP]
    return fallback[:n]


def by_market(db: Session, market: str) -> list[str]:
    return all_symbols(db, market)


def count(db: Session) -> dict:
    total = db.query(orm.Stock).count()
    tw = db.query(orm.Stock).filter(orm.Stock.market == "TW").count()
    us = db.query(orm.Stock).filter(orm.Stock.market == "US").count()
    return {"total": total, "TW": tw, "US": us}
