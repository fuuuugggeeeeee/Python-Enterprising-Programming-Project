"""SQLAlchemy engine and session lifecycle management."""

from contextlib import contextmanager
from typing import Any, Dict, Iterator

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool


class Base(DeclarativeBase):
    pass


class Database:
    """Own the SQLAlchemy engine and provide short-lived sessions."""

    def __init__(self, database_url: str) -> None:
        options: Dict[str, Any] = {"pool_pre_ping": True}
        if database_url.startswith("sqlite"):
            options["connect_args"] = {"check_same_thread": False}
            if ":memory:" in database_url:
                options["poolclass"] = StaticPool
        self.engine: Engine = create_engine(database_url, **options)
        self.session_factory = sessionmaker(
            bind=self.engine,
            autoflush=False,
            expire_on_commit=False,
        )

    @contextmanager
    def session(self) -> Iterator[Session]:
        session = self.session_factory()
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def is_ready(self) -> bool:
        try:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    def dispose(self) -> None:
        self.engine.dispose()
