from __future__ import annotations

import os
import sys
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///./test_auth.db"
os.environ["SMTP_HOST"] = "127.0.0.1"
os.environ["SMTP_PORT"] = "11125"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
import app.routes.auth as auth_routes  # noqa: E402


engine = create_engine("sqlite+pysqlite:///./test_auth.db", connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


def override_get_db() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def reset_db() -> Generator[None, None, None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    auth_routes.send_email = lambda *_args, **_kwargs: None
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def db() -> Generator[Session, None, None]:
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
