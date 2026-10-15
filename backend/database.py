import os
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import Engine, URL, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


_default_database = Path(__file__).resolve().with_name("ecotwin.db")
_database_url = os.getenv("ECOTWIN_DATABASE_URL")

if _database_url:
    engine = create_engine(
        _database_url,
        connect_args={"check_same_thread": False} if _database_url.startswith("sqlite") else {},
    )
else:
    engine = create_engine(
        URL.create("sqlite", database=str(_default_database)),
        connect_args={"check_same_thread": False},
    )

if engine.dialect.name == "sqlite":
    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(connection, _record) -> None:
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def initialize_database(target_engine: Engine = engine) -> None:
    from backend import models  # noqa: F401

    Base.metadata.create_all(bind=target_engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
