"""SQLAlchemy session 與 ORM 基礎類別。"""
from __future__ import annotations

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

DB_URL = settings.database_url or "sqlite:///./stocksim.db"
_is_sqlite = DB_URL.startswith("sqlite")
_connect_args = {"check_same_thread": False} if _is_sqlite else {}

engine = create_engine(DB_URL, connect_args=_connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


if _is_sqlite:
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        if settings.app_mode == "multi":
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _ensure_sqlite_column(table: str, column: str, ddl: str) -> None:
    """SQLite create_all 不會補既有欄位；這裡做保守的 add-column migration。"""
    if not _is_sqlite:
        return
    with engine.begin() as conn:
        exists = inspect(conn).has_table(table)
        if not exists:
            return
        cols = {row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))}
        if column not in cols:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))


def _ensure_sqlite_index(name: str, table: str, column: str) -> None:
    if not _is_sqlite:
        return
    with engine.begin() as conn:
        if inspect(conn).has_table(table):
            conn.execute(text(f"CREATE INDEX IF NOT EXISTS {name} ON {table} ({column})"))


def _ensure_user_schema() -> None:
    _ensure_sqlite_column("portfolios", "user_id", "INTEGER DEFAULT 1")
    _ensure_sqlite_column("recommendation_runs", "user_id", "INTEGER DEFAULT 1")
    _ensure_sqlite_column("recommendations", "user_id", "INTEGER DEFAULT 1")
    _ensure_sqlite_index("ix_portfolios_user_id", "portfolios", "user_id")
    _ensure_sqlite_index("ix_recommendation_runs_user_id", "recommendation_runs", "user_id")
    _ensure_sqlite_index("ix_recommendations_user_id", "recommendations", "user_id")


def init_db() -> None:
    """建立缺漏的資料表 + 確保 single mode default user / portfolio 存在。"""
    from app.models import db as orm  # noqa: F401  匯入以註冊 metadata

    Base.metadata.create_all(bind=engine)
    _ensure_user_schema()

    with SessionLocal() as s:
        local_user = s.query(orm.User).filter(orm.User.id == 1).first()
        if local_user is None:
            s.add(
                orm.User(
                    id=1,
                    provider="local",
                    provider_id="local",
                    email="local@local",
                    name="Local User",
                )
            )
            s.commit()

        existing = s.query(orm.Portfolio).filter(orm.Portfolio.user_id == 1).first()
        if existing is None:
            s.add(
                orm.Portfolio(
                    id=1,
                    user_id=1,
                    name="My Portfolio",
                    initial_cash=1_000_000.0,
                    total_invested=1_000_000.0,
                    cash=1_000_000.0,
                )
            )
            s.commit()
