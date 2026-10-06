"""Integration tests for authentication API endpoints and RBAC dependencies."""

import pytest
from fastapi import APIRouter, Depends, status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.dependencies import (
    get_current_active_superuser,
    get_current_user,
    require_permissions,
    require_roles,
)
from app.auth.security import hash_password
from app.database.models import Permission, Role, User
from app.database.repositories import UserRepository
from app.main import app

# Create a temporary router to test RBAC dependency protections
rbac_test_router = APIRouter(prefix="/test-rbac")


@rbac_test_router.get("/admin-only", dependencies=[Depends(require_roles("AuthAdminRole"))])
def admin_only_endpoint():
    return {"message": "Admin access granted"}


@rbac_test_router.get(
    "/orders-write-only",
    dependencies=[Depends(require_permissions("auth:orders:write"))],
)
def orders_write_endpoint():
    return {"message": "Write orders permission granted"}


@rbac_test_router.get("/superuser-only", dependencies=[Depends(get_current_active_superuser)])
def superuser_only_endpoint():
    return {"message": "Superuser access granted"}


app.include_router(rbac_test_router)


def test_user_registration(client: TestClient) -> None:
    """Verify user registration creates user and returns 201."""
    payload = {
        "email": "newuser@enterprise.ai",
        "password": "SecurePassword123!",
        "full_name": "New Enterprise User",
        "department": "Engineering",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()
    assert data["email"] == "newuser@enterprise.ai"
    assert data["full_name"] == "New Enterprise User"
    assert data["department"] == "Engineering"
    assert data["is_active"] is True
    assert "password" not in data
    assert "hashed_password" not in data


def test_user_registration_duplicate_email(client: TestClient) -> None:
    """Verify duplicate registration returns 409 Conflict."""
    payload = {
        "email": "duplicate@enterprise.ai",
        "password": "SecurePassword123!",
        "full_name": "Duplicate User",
    }
    first_resp = client.post("/api/v1/auth/register", json=payload)
    assert first_resp.status_code == status.HTTP_201_CREATED

    second_resp = client.post("/api/v1/auth/register", json=payload)
    assert second_resp.status_code == status.HTTP_409_CONFLICT


def test_user_login_success_and_me(client: TestClient) -> None:
    """Verify login issues a valid JWT and /me returns authenticated user details."""
    register_payload = {
        "email": "authme@enterprise.ai",
        "password": "ValidPassword999!",
        "full_name": "Auth Me User",
    }
    client.post("/api/v1/auth/register", json=register_payload)

    login_payload = {
        "email": "authme@enterprise.ai",
        "password": "ValidPassword999!",
    }
    login_resp = client.post("/api/v1/auth/login", json=login_payload)
    assert login_resp.status_code == status.HTTP_200_OK

    token_data = login_resp.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
    assert token_data["expires_in"] > 0

    token = token_data["access_token"]

    # Access /me with Bearer token
    me_resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_resp.status_code == status.HTTP_200_OK
    user_data = me_resp.json()
    assert user_data["email"] == "authme@enterprise.ai"
    assert user_data["full_name"] == "Auth Me User"


def test_user_login_invalid_credentials(client: TestClient) -> None:
    """Verify invalid password returns 401 Unauthorized."""
    payload = {
        "email": "testinvalid@enterprise.ai",
        "password": "RealPassword123!",
        "full_name": "Test Invalid",
    }
    client.post("/api/v1/auth/register", json=payload)

    # Wrong password
    bad_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "testinvalid@enterprise.ai", "password": "WrongPassword!"},
    )
    assert bad_resp.status_code == status.HTTP_401_UNAUTHORIZED

    # Non-existent user
    notfound_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@enterprise.ai", "password": "AnyPassword123!"},
    )
    assert notfound_resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_auth_me_unauthorized(client: TestClient) -> None:
    """Verify calling /me without authorization header or with invalid token fails."""
    no_auth = client.get("/api/v1/auth/me")
    assert no_auth.status_code == status.HTTP_401_UNAUTHORIZED

    invalid_token = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer completely-invalid-token"},
    )
    assert invalid_token.status_code == status.HTTP_401_UNAUTHORIZED


def test_rbac_roles_and_permissions(client: TestClient, db_session: Session) -> None:
    """Verify fine-grained role and permission enforcement."""
    perm_read = Permission(name="auth:orders:read", resource="orders", action="read")
    perm_write = Permission(name="auth:orders:write", resource="orders", action="write")
    db_session.add_all([perm_read, perm_write])
    db_session.flush()

    role_operator = Role(name="AuthOperatorRole", description="Operator")
    role_operator.permissions = [perm_read]

    role_admin = Role(name="AuthAdminRole", description="Administrator")
    role_admin.permissions = [perm_read, perm_write]

    db_session.add_all([role_operator, role_admin])
    db_session.flush()

    # User 1: Regular operator (only auth:orders:read, no AuthAdminRole, no auth:orders:write)
    user_op = User(
        email="operator_test@enterprise.ai",
        hashed_password=hash_password("OperatorPass123!"),
        full_name="Operator User",
    )
    user_op.roles = [role_operator]

    # User 2: Admin user (AuthAdminRole, auth:orders:write permission)
    user_admin = User(
        email="admin_test@enterprise.ai",
        hashed_password=hash_password("AdminPass123!"),
        full_name="Admin User",
    )
    user_admin.roles = [role_admin]

    # User 3: Superuser
    user_super = User(
        email="super_test@enterprise.ai",
        hashed_password=hash_password("SuperPass123!"),
        full_name="Super User",
        is_superuser=True,
    )

    db_session.add_all([user_op, user_admin, user_super])
    db_session.commit()

    # Login as operator
    op_login = client.post(
        "/api/v1/auth/login",
        json={"email": "operator_test@enterprise.ai", "password": "OperatorPass123!"},
    )
    assert op_login.status_code == status.HTTP_200_OK
    op_token = op_login.json()["access_token"]

    # Login as admin
    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_test@enterprise.ai", "password": "AdminPass123!"},
    )
    assert admin_login.status_code == status.HTTP_200_OK
    admin_token = admin_login.json()["access_token"]

    # Login as superuser
    super_login = client.post(
        "/api/v1/auth/login",
        json={"email": "super_test@enterprise.ai", "password": "SuperPass123!"},
    )
    assert super_login.status_code == status.HTTP_200_OK
    super_token = super_login.json()["access_token"]

    # Operator accessing /test-rbac/admin-only -> 403 Forbidden
    op_admin_resp = client.get(
        "/test-rbac/admin-only",
        headers={"Authorization": f"Bearer {op_token}"},
    )
    assert op_admin_resp.status_code == status.HTTP_403_FORBIDDEN

    # Operator accessing /test-rbac/orders-write-only -> 403 Forbidden
    op_perm_resp = client.get(
        "/test-rbac/orders-write-only",
        headers={"Authorization": f"Bearer {op_token}"},
    )
    assert op_perm_resp.status_code == status.HTTP_403_FORBIDDEN

    # Admin accessing /test-rbac/admin-only -> 200 OK
    admin_resp = client.get(
        "/test-rbac/admin-only",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert admin_resp.status_code == status.HTTP_200_OK

    # Admin accessing /test-rbac/orders-write-only -> 200 OK
    admin_perm_resp = client.get(
        "/test-rbac/orders-write-only",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert admin_perm_resp.status_code == status.HTTP_200_OK

    # Superuser bypasses role and permission checks
    super_admin_resp = client.get(
        "/test-rbac/admin-only",
        headers={"Authorization": f"Bearer {super_token}"},
    )
    assert super_admin_resp.status_code == status.HTTP_200_OK

    super_perm_resp = client.get(
        "/test-rbac/orders-write-only",
        headers={"Authorization": f"Bearer {super_token}"},
    )
    assert super_perm_resp.status_code == status.HTTP_200_OK

    super_only_resp = client.get(
        "/test-rbac/superuser-only",
        headers={"Authorization": f"Bearer {super_token}"},
    )
    assert super_only_resp.status_code == status.HTTP_200_OK
