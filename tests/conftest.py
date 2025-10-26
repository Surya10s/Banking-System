# File: tests/conftest.py
"""Pytest configuration and fixtures."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from datetime import date

from main import app
from api.dependencies import get_db
import schemas

# Create in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    schemas.Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        schemas.Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with database dependency override."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_users(db_session):
    """Create sample users for testing."""
    users = [
        schemas.User(
            id=1,
            username="user1",
            AccountNo=1000000001,
            Amount=5000,
            daily_used=2000,
            last_reset=date.today()
        ),
        schemas.User(
            id=2,
            username="user2",
            AccountNo=1000000002,
            Amount=3000,
            daily_used=2000,
            last_reset=date.today()
        ),
        schemas.User(
            id=3,
            username="user3",
            AccountNo=1000000003,
            Amount=1000,
            daily_used=2000,
            last_reset=date.today()
        ),
    ]
    db_session.add_all(users)
    db_session.commit()
    for user in users:
        db_session.refresh(user)
    return users