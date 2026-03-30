# backend/tests/conftest.py
import tempfile
import shutil
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

# Explicit model imports -- required before create_all()
from app.models.test import Test  # noqa: F401
from app.models.screen_question import ScreenQuestion  # noqa: F401
from app.models.option import Option  # noqa: F401
from app.models.response import Response  # noqa: F401
from app.database import get_session
from main import app


# In-memory SQLite with StaticPool for test isolation
test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(test_engine, "connect")
def _set_test_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def get_test_session():
    with Session(test_engine) as session:
        yield session


@pytest.fixture(autouse=True)
def setup_db():
    SQLModel.metadata.create_all(test_engine)
    yield
    SQLModel.metadata.drop_all(test_engine)


@pytest.fixture(autouse=True)
def media_dir(monkeypatch, tmp_path):
    """Monkeypatch MEDIA_DIR to a temp directory to isolate tests from production."""
    import app.config as config
    import app.services.image_service as img_svc
    monkeypatch.setattr(config, "MEDIA_DIR", tmp_path)
    monkeypatch.setattr(img_svc, "MEDIA_DIR", tmp_path)
    return tmp_path


@pytest.fixture
def client():
    app.dependency_overrides[get_session] = get_test_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
