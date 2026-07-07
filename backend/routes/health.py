"""Health check endpoints for the Application Layer."""

from typing import Any, Dict

from fastapi import APIRouter

from config import get_settings

router = APIRouter()


@router.get("/health")
def health_check() -> Dict[str, Any]:
    settings = get_settings()
    return {
        "status": "healthy",
        "application": {
            "name": settings.application.name,
            "version": settings.application.version,
            "layer": "application",
        },
        "version": settings.application.version,
    }


@router.get("/version")
def version_info() -> Dict[str, str]:
    settings = get_settings()
    return {
        "application": settings.application.name,
        "version": settings.application.version,
        "layer": "application",
        "python": __import__("sys").version,
    }
