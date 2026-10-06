"""Unit tests for password hashing and JWT token operations."""

from datetime import timedelta
import pytest
from jose import JWTError

from app.auth.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hashing_and_verification() -> None:
    """Verify that password hashing generates verifiable bcrypt hashes."""
    raw_password = "SuperSecretPassword123!"
    hashed = hash_password(raw_password)

    assert hashed != raw_password
    assert hashed.startswith("$2b$")
    assert verify_password(raw_password, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False
    assert verify_password("", hashed) is False
    assert verify_password(raw_password, "") is False


def test_create_and_decode_access_token() -> None:
    """Verify that JWT tokens encode and decode claims faithfully."""
    subject = "user_42"
    extra_claims = {
        "email": "agent@enterprise.ai",
        "roles": ["Admin", "Operator"],
        "permissions": ["orders:read", "orders:write"],
    }
    token = create_access_token(
        subject=subject,
        expires_delta=timedelta(minutes=30),
        extra_claims=extra_claims,
    )

    payload = decode_access_token(token)
    assert payload["sub"] == "user_42"
    assert payload["email"] == "agent@enterprise.ai"
    assert payload["roles"] == ["Admin", "Operator"]
    assert payload["permissions"] == ["orders:read", "orders:write"]
    assert "exp" in payload
    assert "iat" in payload


def test_expired_token_raises_jwterror() -> None:
    """Verify that an expired JWT token raises a JWTError when decoded."""
    token = create_access_token(
        subject="expired_user",
        expires_delta=timedelta(seconds=-10),
    )
    with pytest.raises(JWTError):
        decode_access_token(token)


def test_invalid_token_signature_raises_jwterror() -> None:
    """Verify that a forged or malformed token raises a JWTError."""
    fake_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalidpayload.invalidsignature"
    with pytest.raises(JWTError):
        decode_access_token(fake_token)
