"""Main API router aggregating all route modules."""

from fastapi import APIRouter

from backend.api.health import router as health_router

# Top-level application router
api_router = APIRouter()

# Include sub-routers
api_router.include_router(health_router, tags=["health"])
