"""Authentication and authorization package."""

from app.auth.dependencies import (
    get_current_active_superuser,
    get_current_user,
    oauth2_scheme,
    require_permissions,
    require_roles,
)
from app.auth.schemas import (
    RoleResponse,
    Token,
    TokenPayload,
    UserLogin,
    UserRegister,
    UserResponse,
)
from app.auth.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

__all__ = [
    "RoleResponse",
    "Token",
    "TokenPayload",
    "UserLogin",
    "UserRegister",
    "UserResponse",
    "create_access_token",
    "decode_access_token",
    "get_current_active_superuser",
    "get_current_user",
    "hash_password",
    "oauth2_scheme",
    "require_permissions",
    "require_roles",
    "verify_password",
]
