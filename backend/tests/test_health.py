"""Tests for the health check endpoints."""

import pytest
from fastapi import status
from fastapi.testclient import TestClient


def test_health_check_root(client: TestClient) -> None:
    """Verify that GET /health returns 200 OK and expected JSON schema."""
    response = client.get("/health")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["status"] == "healthy"
    assert data["app_name"] == "Enterprise Agent Platform Test"
    assert data["environment"] == "test"
    assert "version" in data


def test_health_check_api_v1(client: TestClient) -> None:
    """Verify that GET /api/v1/health returns 200 OK and matching status."""
    response = client.get("/api/v1/health")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["status"] == "healthy"
    assert data["environment"] == "test"


def test_health_check_response_structure(client: TestClient) -> None:
    """Verify exact payload keys on health check response."""
    response = client.get("/health")
    assert response.status_code == status.HTTP_200_OK

    expected_keys = {"status", "app_name", "version", "environment"}
    assert set(response.json().keys()) == expected_keys
