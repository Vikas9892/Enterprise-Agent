"""FastAPI authentication and RBAC authorization dependencies."""

from typing import Callable, List, Set
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.auth.security import decode_access_token
from app.core.config import get_settings
from app.database.models.user import User
from app.database.repositories.user import UserRepository
from app.database.session import get_db

settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.api_v1_str}/auth/login",
    auto_error=True,
)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Validate bearer token and return authenticated active user entity."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        subject: str = payload.get("sub")
        if subject is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user_repo = UserRepository(db)
    if subject.isdigit():
        user = user_repo.get_with_roles(int(subject))
    else:
        user = user_repo.get_by_email(subject)

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account",
        )

    return user


def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """Verify that authenticated user holds superuser administrative privileges."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser privileges required for this operation",
        )
    return current_user


def require_roles(*allowed_roles: str) -> Callable[[User], User]:
    """Factory creating dependency to require at least one matching role."""

    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.is_superuser:
            return current_user

        user_roles = {r.name for r in current_user.roles}
        if not any(r in user_roles for r in allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires one of the following roles: {', '.join(allowed_roles)}",
            )
        return current_user

    return role_checker


def require_permissions(*required_permissions: str) -> Callable[[User], User]:
    """Factory creating dependency to verify all specified permissions are granted."""

    def permission_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.is_superuser:
            return current_user

        user_permissions: Set[str] = {
            perm.name for role in current_user.roles for perm in role.permissions
        }

        missing_permissions = [p for p in required_permissions if p not in user_permissions]
        if missing_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permission(s): {', '.join(missing_permissions)}",
            )
        return current_user

    return permission_checker
