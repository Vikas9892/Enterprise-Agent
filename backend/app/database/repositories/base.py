"""Base repository implementation defining common generic CRUD operations."""

from typing import Any, Generic, List, Optional, Type, TypeVar
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Generic repository providing standardized persistence operations."""

    def __init__(self, model: Type[ModelType], session: Session) -> None:
        self.model = model
        self.session = session

    def get_by_id(self, id: int) -> Optional[ModelType]:
        """Retrieve a single record by primary key."""
        return self.session.get(self.model, id)

    def list(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """Retrieve a paginated list of records."""
        statement = select(self.model).offset(skip).limit(limit)
        return list(self.session.scalars(statement).all())

    def count(self) -> int:
        """Return total row count for the entity."""
        statement = select(func.count()).select_from(self.model)
        result = self.session.execute(statement).scalar()
        return result or 0

    def create(self, **kwargs: Any) -> ModelType:
        """Instantiate, persist, and flush a new record."""
        instance = self.model(**kwargs)
        self.session.add(instance)
        self.session.flush()
        return instance

    def update(self, instance: ModelType, **kwargs: Any) -> ModelType:
        """Apply attributes to an existing record and flush."""
        for key, value in kwargs.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        self.session.flush()
        return instance

    def delete(self, instance: ModelType) -> None:
        """Remove a record and flush."""
        self.session.delete(instance)
        self.session.flush()
