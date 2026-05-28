"""推薦選股 API：背景掃描 + 結果查詢。"""
from __future__ import annotations

import logging
import threading
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.session import get_current_user
from app.db import SessionLocal, get_db
from app.data import listings
from app.models import db as orm
from app.services import recommend_service

logger = logging.getLogger(__name__)

router = APIRouter()


# 進程內的進度（不放 DB，避免每秒寫入；DB 只記 final 結果）
_progress_lock = threading.Lock()
_progress: dict[int, dict] = {}  # run_id -> {scanned, matched, total}


class ScanRequest(BaseModel):
    horizon: int
    universe: str = "top500"  # top500 / tw / us / all


def _bg_scan(run_id: int, horizon: int, universe_kind: str, user_id: int) -> None:
    db = SessionLocal()
    try:
        run = db.query(orm.RecommendationRun).filter(orm.RecommendationRun.id == run_id).first()
        if run is None:
            return
        run.status = "running"
        db.commit()

        def on_progress(scanned: int, matched: int, total: int) -> None:
            with _progress_lock:
                _progress[run_id] = {"scanned": scanned, "matched": matched, "total": total}
            run.scanned = scanned
            run.matched = matched
            run.total = total
            db.commit()

        out = recommend_service.scan(
            db, horizon=horizon, universe_kind=universe_kind, on_progress=on_progress
        )
        recommend_service.save_run(db, run_id, out["results"], user_id=user_id)

        run.status = "done"
        run.scanned = out["scanned"]
        run.matched = out["matched"]
        run.total = out["total"]
        run.finished_at = datetime.utcnow()
        db.commit()
        logger.info("scan done: horizon=%d matched=%d/%d", horizon, run.matched, run.total)
    except Exception as e:
        logger.exception("scan failed: %s", e)
        try:
            run = db.query(orm.RecommendationRun).filter(orm.RecommendationRun.id == run_id).first()
            if run is not None:
                run.status = "failed"
                run.error = str(e)[:500]
                run.finished_at = datetime.utcnow()
                db.commit()
        except Exception:
            pass
    finally:
        with _progress_lock:
            _progress.pop(run_id, None)
        db.close()


@router.get("/horizons")
def get_horizons() -> list[dict]:
    return [
        {"horizon": h, "strategy": name}
        for h, (name, _) in recommend_service.HORIZON_STRATEGY.items()
    ]


@router.get("/latest")
def get_latest(
    horizon: int,
    limit: int = 30,
    db: Session = Depends(get_db),
    current_user: orm.User = Depends(get_current_user),
) -> dict:
    run = recommend_service.latest_run(db, horizon, current_user.id)
    if run is None:
        return {"horizon": horizon, "run": None, "results": []}
    return {
        "horizon": horizon,
        "run": {
            "id": run.id,
            "status": run.status,
            "started_at": run.started_at.isoformat(),
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "scanned": run.scanned,
            "matched": run.matched,
            "total": run.total,
            "universe": run.universe,
        },
        "results": recommend_service.list_recommendations(
            db, run.id, limit=limit, user_id=current_user.id
        ),
    }


@router.post("/scan")
def trigger_scan(
    req: ScanRequest,
    bg: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: orm.User = Depends(get_current_user),
) -> dict:
    if req.horizon not in recommend_service.HORIZON_STRATEGY:
        raise HTTPException(status_code=400, detail=f"unknown horizon: {req.horizon}")

    # 同 horizon 已有 running，回傳該 run
    existing = (
        db.query(orm.RecommendationRun)
        .filter(
            orm.RecommendationRun.horizon == req.horizon,
            orm.RecommendationRun.user_id == current_user.id,
            orm.RecommendationRun.status.in_(("pending", "running")),
        )
        .first()
    )
    if existing:
        return {"run_id": existing.id, "status": existing.status, "horizon": existing.horizon}

    run = orm.RecommendationRun(
        user_id=current_user.id,
        horizon=req.horizon,
        universe=req.universe,
        status="pending",
        started_at=datetime.utcnow(),
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    bg.add_task(_bg_scan, run.id, req.horizon, req.universe, current_user.id)
    return {"run_id": run.id, "status": "pending", "horizon": req.horizon}


@router.get("/scan/{run_id}")
def scan_status(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: orm.User = Depends(get_current_user),
) -> dict:
    run = (
        db.query(orm.RecommendationRun)
        .filter(
            orm.RecommendationRun.id == run_id,
            orm.RecommendationRun.user_id == current_user.id,
        )
        .first()
    )
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")

    with _progress_lock:
        live = _progress.get(run_id)

    return {
        "id": run.id,
        "horizon": run.horizon,
        "status": run.status,
        "scanned": live["scanned"] if live else run.scanned,
        "matched": live["matched"] if live else run.matched,
        "total": live["total"] if live else run.total,
        "started_at": run.started_at.isoformat(),
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "error": run.error,
    }


class SeedRequest(BaseModel):
    full: bool = False


@router.post("/seed-universe")
def seed_universe(req: SeedRequest, db: Session = Depends(get_db)) -> dict:
    """灌股票池：full=False 只灌內建 Top；full=True 從交易所 API 拉全部。"""
    seeded = listings.seed_top(db)
    if not req.full:
        from app.data import universe
        return {"seeded_top": seeded, **universe.count(db)}

    full_counts = listings.fetch_all(db)
    from app.data import universe
    return {"seeded_top": seeded, **full_counts, **universe.count(db)}