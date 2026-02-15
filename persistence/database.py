from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DEFAULT_DB_PATH = Path("data/insighthub.db")


class Base(DeclarativeBase):
    pass


def build_sqlite_url(db_path: str | Path = DEFAULT_DB_PATH) -> str:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{path.as_posix()}"


def create_sqlite_engine(db_path: str | Path = DEFAULT_DB_PATH):
    return create_engine(build_sqlite_url(db_path), future=True)


def create_session_factory(db_path: str | Path = DEFAULT_DB_PATH):
    engine = create_sqlite_engine(db_path)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
