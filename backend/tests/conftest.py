# backend/tests/conftest.py
"""Test configuration: use an in-memory SQLite database with StaticPool to isolate tests."""
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, text
from app.database import get_session

# Explicit model imports BEFORE create_all to ensure metadata is registered
from app.models import Test, ScreenQuestion, Option, Response  # noqa: F401

# In-memory SQLite for test isolation -- StaticPool ensures the same connection
# is reused across threads, which is required for in-memory SQLite.
TEST_DATABASE_URL = "sqlite://"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@pytest.fixture(name="test_media_dir", autouse=True)
def test_media_dir_fixture(tmp_path, monkeypatch):
    """Isolate media writes from production backend/media/ directory.

    Creates a per-test temp directory and monkeypatches MEDIA_DIR in both
    config and image_service modules.
    """
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    monkeypatch.setattr("app.config.MEDIA_DIR", media_dir)
    monkeypatch.setattr("app.services.image_service.MEDIA_DIR", media_dir)
    return media_dir


@pytest.fixture(name="session", autouse=True)
def session_fixture():
    """Create fresh tables for each test, yield session, then drop."""
    # Enable foreign keys before creating tables
    with test_engine.connect() as conn:
        conn.execute(text("PRAGMA foreign_keys=ON"))
        conn.commit()
    SQLModel.metadata.create_all(test_engine)
    with Session(test_engine) as session:
        yield session
    SQLModel.metadata.drop_all(test_engine)


@pytest.fixture(name="client")
def client_fixture(session: Session, test_media_dir):
    """TestClient that uses the test database session.

    Depends on test_media_dir to ensure media isolation is set up before
    the app is loaded.
    """
    def get_session_override():
        yield session

    from main import app
    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()
