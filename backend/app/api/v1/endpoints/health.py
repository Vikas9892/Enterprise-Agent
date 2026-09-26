"""Health check endpoint definition and response models."""

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from app.core.config import Settings, get_settings

router = APIRouter()


class HealthResponse(BaseModel):
    """Schema representing the health check response payload."""

    status: str = Field(
        default="healthy",
        description="Current health status indicator",
        examples=["healthy"],
    )
    app_name: str = Field(
        description="Application service name",
        examples=["Enterprise Agent Platform"],
    )
    version: str = Field(
        description="Application version",
        examples=["0.1.0"],
    )
    environment: str = Field(
        description="Deployment environment (development, staging, production, test)",
        examples=["development"],
    )


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health check",
    description="Returns JSON indicating that the API service is operational and healthy.",
    tags=["Health"],
)
async def health_check(
    settings: Settings = Depends(get_settings),
) -> HealthResponse:
    """Verify service health and return operational status."""
    return HealthResponse(
        status="healthy",
        app_name=settings.app_name,
        version=settings.version,
        environment=settings.app_env,
    )
