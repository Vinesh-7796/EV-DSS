"""FastAPI application factory for EV-DDSS."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from backend.api.router import api_router
from backend.logger import logger
from config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager.

    Handles startup and shutdown events without deprecated decorators.
    """
    logger.info("FastAPI application started")
    yield
    logger.info("FastAPI application shutting down")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance.

    Returns:
        Configured FastAPI application.
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.application.name,
        version=settings.application.version,
        description="EV Diagnostic Decision Support System - AI-powered vehicle diagnostics",
        debug=settings.application.debug,
        docs_url="/docs" if settings.application.debug else None,
        redoc_url="/redoc" if settings.application.debug else None,
        lifespan=lifespan,
    )

    # Register main router
    app.include_router(api_router)

    # Root endpoint
    @app.get("/")
    def root() -> Dict[str, str]:
        """Root endpoint returning basic application info."""
        return {
            "application": settings.application.name,
            "version": settings.application.version,
            "status": "running",
        }

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Catch unhandled exceptions and return a structured error response."""
        logger.error("Unhandled exception: {} | Path: {}", exc, request.url)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "path": str(request.url)},
        )

    return app
