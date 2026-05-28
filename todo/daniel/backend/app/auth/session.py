"""Auth dependency skeleton.

PR1 只建立模式切換基礎：
- single mode 永遠回本機 user_id=1
- multi mode 先回 401，後續 OAuth PR 再接 cookie session
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import db as orm


def _get_or_create_local_user(db: Session) -> orm.User:
    user = db.query(orm.User).filter(orm.User.id == 1).first()
    if user is None:
        user = orm.User(
            id=1,
            provider="local",
            provider_id="local",
            email="local@local",
            name="Local User",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def get_current_user(db: Session = Depends(get_db)) -> orm.User:
    if settings.app_mode == "single":
        return _get_or_create_local_user(db)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="login required (OAuth will be enabled in multi-user mode)",
    )
