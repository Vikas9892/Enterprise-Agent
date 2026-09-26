"""User repository managing system users and RBAC assignments."""

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database.models.user import Role, User
from app.database.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Data access operations for User entities."""

    def __init__(self, session: Session) -> None:
        super().__init__(User, session)

    def get_by_email(self, email: str) -> Optional[User]:
        """Fetch user by unique email address with eager loaded roles."""
        stmt = (
            select(User)
            .where(User.email == email.strip().lower())
            .options(selectinload(User.roles).selectinload(Role.permissions))
        )
        return self.session.scalars(stmt).first()

    def get_with_roles(self, user_id: int) -> Optional[User]:
        """Fetch user by ID with roles and permissions eagerly loaded."""
        stmt = (
            select(User)
            .where(User.id == user_id)
            .options(selectinload(User.roles).selectinload(Role.permissions))
        )
        return self.session.scalars(stmt).first()

    def list_active(self, skip: int = 0, limit: int = 50) -> List[User]:
        """List active users."""
        stmt = (
            select(User)
            .where(User.is_active.is_(True))
            .options(selectinload(User.roles))
            .offset(skip)
            .limit(limit)
        )
        return list(self.session.scalars(stmt).all())

    def assign_role(self, user: User, role: Role) -> User:
        """Attach a role to a user if not already present."""
        if role not in user.roles:
            user.roles.append(role)
            self.session.flush()
        return user
