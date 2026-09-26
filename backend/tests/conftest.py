"""Pytest test fixtures and configuration."""

from typing import Generator
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app


def get_test_settings() -> Settings:
    """Return test settings with predictable defaults."""
    return Settings(
        app_name="Enterprise Agent Platform Test",
        app_env="test",
        debug=True,
        log_level="DEBUG",
        log_format="text",
    )


@pytest.fixture(scope="session")
def client() -> Generator[TestClient, None, None]:
    """TestClient fixture with test settings dependency override."""
    app.dependency_overrides[get_settings] = get_test_settings
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
