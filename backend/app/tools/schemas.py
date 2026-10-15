"""Schemas and data models for tools execution and registry."""

from typing import Any, Callable, Dict, Optional
from pydantic import BaseModel, Field


class ToolExecutionContext(BaseModel):
    """Contextual metadata passed to tools during execution."""

    user_id: Optional[int] = None
    session_id: Optional[str] = None
    roles: list[str] = Field(default_factory=list)


class ToolMetadata(BaseModel):
    """Metadata describing a callable tool."""

    name: str
    description: str
    parameters: Dict[str, Any]
    is_sensitive: bool = False
    requires_approval: bool = False
