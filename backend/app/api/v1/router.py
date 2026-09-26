"""API v1 master router aggregating version 1 endpoints."""

from fastapi import APIRouter
from app.api.v1.endpoints.health import router as health_router

v1_router = APIRouter()

# Register endpoint routers
v1_router.include_router(health_router)
