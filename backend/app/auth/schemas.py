"""Pydantic schemas for authentication and authorization."""

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class Token(BaseModel):
    """Schema representing an issued JWT token response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenPayload(BaseModel):
    """Schema representing decoded JWT payload claims."""

    sub: Optional[str] = None
    exp: Optional[int] = None
    email: Optional[str] = None
    roles: List[str] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=list)


class UserLogin(BaseModel):
    """Schema for authenticating existing users."""

    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class UserRegister(BaseModel):
    """Schema for registering a new user."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=100)
    department: Optional[str] = Field(default=None, max_length=100)


class RoleResponse(BaseModel):
    """Schema representing a role."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str] = None
    is_system_role: bool = False


class UserResponse(BaseModel):
    """Schema representing authenticated user profile."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    department: Optional[str] = None
    is_active: bool
    is_superuser: bool
    roles: List[str] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=list)
