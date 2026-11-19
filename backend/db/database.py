"""SQLite engine with BEGIN IMMEDIATE transactions so writers are serialised.

Every `transaction()` block is one atomic DB transaction: it commits on normal exit and
rolls back on any exception.
"""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from backend.models import entities as _entities  # noqa: F401  (register tables)
from backend.models.base import Base


class Database:
    def __init__(self, url: str) -> None:
        self.engine = create_engine(url, connect_args={"check_same_thread": False, "timeout": 30})

        @event.listens_for(self.engine, "connect")
        def _on_connect(dbapi_conn, _record):  # type: ignore[no-untyped-def]
            dbapi_conn.isolation_level = None  # let SQLAlchemy emit BEGIN itself
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.execute("PRAGMA busy_timeout=30000")
            cur.execute("PRAGMA journal_mode=WAL")
            cur.close()

        @event.listens_for(self.engine, "begin")
        def _on_begin(conn):  # type: ignore[no-untyped-def]
            conn.exec_driver_sql("BEGIN IMMEDIATE")

        self._session_factory = sessionmaker(self.engine, expire_on_commit=False)

    def create_all(self) -> None:
        Base.metadata.create_all(self.engine)

    @contextmanager
    def transaction(self) -> Iterator[Session]:
        session = self._session_factory()
        try:
            with session.begin():
                yield session
        finally:
            session.close()

    def dispose(self) -> None:
        self.engine.dispose()
