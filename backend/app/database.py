from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlsplit

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import NullPool


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DATABASE_PATH = BASE_DIR / "data.db"


def normalize_database_url(database_url: str) -> str:
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    if database_url.startswith("postgresql://") and "+psycopg" not in database_url.split("://", 1)[0]:
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return database_url


def is_sqlite_url(database_url: str) -> bool:
    return database_url.startswith("sqlite")


def is_postgres_url(database_url: str) -> bool:
    return database_url.startswith("postgresql") or database_url.startswith("postgres://")


def uses_transaction_pooler(database_url: str) -> bool:
    parsed = urlsplit(database_url)
    pool_mode = os.getenv("REDOCENCIA_DB_POOL_MODE", "").strip().lower()
    return pool_mode == "transaction" or parsed.port == 6543


def resolve_database_url() -> str:
    configured_url = (os.getenv("DATABASE_URL") or "").strip()
    configured_url = configured_url.replace("\\r", "").replace("\\n", "").replace("\r", "").replace("\n", "")
    if configured_url:
        return normalize_database_url(configured_url)

    if os.getenv("VERCEL"):
        raise RuntimeError("DATABASE_URL must be configured on Vercel. SQLite fallback is disabled.")

    return f"sqlite:///{DEFAULT_DATABASE_PATH.as_posix()}"


DATABASE_URL = resolve_database_url()


class Base(DeclarativeBase):
    pass


engine_kwargs: dict = {}

if is_sqlite_url(DATABASE_URL):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
elif is_postgres_url(DATABASE_URL):
    connect_args = {"sslmode": os.getenv("REDOCENCIA_DB_SSLMODE", "require")}
    engine_kwargs["pool_pre_ping"] = True
    if uses_transaction_pooler(DATABASE_URL):
        connect_args["prepare_threshold"] = None
        engine_kwargs["poolclass"] = NullPool
    engine_kwargs["connect_args"] = connect_args

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
