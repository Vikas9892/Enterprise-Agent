"""Authentication endpoints for user registration, login, and profile access."""

from typing import List, Set
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.schemas import Token, UserLogin, UserRegister, UserResponse
from app.auth.security import create_access_token, hash_password, verify_password
from app.core.config import get_settings
from app.database.models.user import User
from app.database.repositories.user import UserRepository
from app.database.session import get_db

router = APIRouter()
settings = get_settings()


def _format_user_response(user: User) -> UserResponse:
    """Format SQLAlchemy User model into UserResponse schema."""
    roles = [role.name for role in user.roles]
    permissions: Set[str] = {
        perm.name for role in user.roles for perm in role.permissions
    }
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        department=user.department,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        roles=roles,
        permissions=sorted(list(permissions)),
    )


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user",
    description="Registers a new platform user with hashed password credentials.",
)
def register(
    payload: UserRegister,
    db: Session = Depends(get_db),
) -> UserResponse:
    """Register a new user account."""
    user_repo = UserRepository(db)
    existing_user = user_repo.get_by_email(payload.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email address already exists",
        )

    user = User(
        email=payload.email.lower().strip(),
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name.strip(),
        department=payload.department.strip() if payload.department else None,
        is_active=True,
        is_superuser=False,
    )
    created_user = user_repo.create(user)
    return _format_user_response(created_user)


@router.post(
    "/login",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary="User login",
    description="Authenticates credentials and returns a signed JWT access token.",
)
def login(
    credentials: UserLogin,
    db: Session = Depends(get_db),
) -> Token:
    """Authenticate user credentials and issue JWT token."""
    user_repo = UserRepository(db)
    user = user_repo.get_by_email(credentials.email)

    if not user or not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account",
        )

    roles = [role.name for role in user.roles]
    permissions = sorted(
        list({perm.name for role in user.roles for perm in role.permissions})
    )

    token = create_access_token(
        subject=user.id,
        extra_claims={
            "email": user.email,
            "roles": roles,
            "permissions": permissions,
        },
    )

    return Token(
        access_token=token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user profile",
    description="Returns the profile and effective RBAC permissions of the authenticated user.",
)
def read_current_user_profile(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Return profile and permissions for the currently authenticated user."""
    return _format_user_response(current_user)
