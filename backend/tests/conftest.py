"""Pytest test fixtures and configuration."""

from typing import Generator
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings, get_settings
from app.database.base import Base
from app.database.session import get_db, set_custom_engine
from app.main import app

# Create in-memory SQLite engine for fast, isolated test execution
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

from sqlalchemy import event


@event.listens_for(test_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
    expire_on_commit=False,
)


def get_test_settings() -> Settings:
    """Return test settings with predictable defaults."""
    return Settings(
        app_name="Enterprise Agent Platform Test",
        app_env="test",
        debug=True,
        log_level="DEBUG",
        log_format="text",
        database_url=TEST_DATABASE_URL,
    )


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Create all schema tables once per test session."""
    set_custom_engine(test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """Provide a transactional database session per test function with automatic rollback."""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="session")
def client() -> Generator[TestClient, None, None]:
    """TestClient fixture with test settings dependency override."""
    app.dependency_overrides[get_settings] = get_test_settings

    def override_get_db():
        with TestingSessionLocal() as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
