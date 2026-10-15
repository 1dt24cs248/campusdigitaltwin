from pathlib import Path

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from fastapi.testclient import TestClient

from backend.database import Base, get_db
from backend import main, models  # noqa: F401
from backend.main import app
from backend.services.data_importer import import_datasets


DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "raw" / "ecotwin_dataset"


@pytest.fixture
def test_engine(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(connection, _record):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def db_session(test_engine):
    testing_session = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)
    with testing_session() as session:
        yield session


@pytest.fixture
def client(test_engine, monkeypatch):
    testing_session = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)

    def override_get_db():
        with testing_session() as session:
            yield session

    monkeypatch.setattr(main, "engine", test_engine)
    monkeypatch.setattr(main, "initialize_database", lambda: Base.metadata.create_all(bind=test_engine))
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def seeded_client(client, test_engine):
    with Session(test_engine) as session:
        import_datasets(DATA_DIR, session)
    return client
