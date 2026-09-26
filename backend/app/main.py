"""FastAPI application entrypoint and lifecycle management."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.api.v1.endpoints.health import router as health_router
from app.core.config import Settings, get_settings
from app.core.logging import get_logger, setup_logging

logger = get_logger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifecycle manager for startup and shutdown events."""
    settings = get_settings()

    # Configure structured logging
    setup_logging(log_level=settings.log_level, log_format=settings.log_format)

    logger.info(
        "Starting Enterprise Agent API",
        extra={
            "app_name": settings.app_name,
            "environment": settings.app_env,
            "version": settings.version,
            "debug": settings.debug,
        },
    )

    yield

    logger.info("Shutting down Enterprise Agent API")


def create_application() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        debug=settings.debug,
        openapi_url=f"{settings.api_v1_str}/openapi.json" if not settings.debug else "/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # Configure CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Direct root health check (e.g. GET /health)
    app.include_router(health_router, tags=["Health"])

    # Versioned API routes (e.g. GET /api/v1/health)
    app.include_router(api_router, prefix="/api")

    return app


app = create_application()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
