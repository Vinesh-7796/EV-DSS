"""Health check endpoints for EV-DDSS.

Provides routes to verify application status, database connectivity,
Qdrant connectivity, and configuration state.
"""

from typing import Any, Dict

from fastapi import APIRouter

from backend.logger import logger
from config import get_settings
from database.connection import get_database
from database.qdrant import get_qdrant

router = APIRouter()


@router.get("/health")
def health_check() -> Dict[str, Any]:
    """Comprehensive health check endpoint.

    Verifies:
        - Application is running
        - Database is reachable
        - Qdrant is reachable
        - Configuration is loaded

    Returns:
        JSON object with overall health status and component statuses.
    """
    settings = get_settings()
    db = get_database()
    qdrant = get_qdrant()

    # Database status
    db_status: str = "connected" if db.is_connected else "disconnected"
    if db.is_connected:
        try:
            with db.get_session() as session:
                from sqlalchemy import text
                result = session.execute(text("SELECT 1"))
                if result.fetchone():
                    db_status = "connected"
        except Exception:
            db_status = "error"

    # Qdrant status
    qdrant_status: str = "connected" if qdrant.is_connected else "disconnected"
    if qdrant.is_connected:
        try:
            qdrant_health = qdrant.health_check()
            qdrant_status = qdrant_health.get("status", "error")
        except Exception:
            qdrant_status = "error"

    # Overall status
    all_healthy = all(
        s == "connected" or s == "healthy"
        for s in [db_status, qdrant_status]
    )

    response: Dict[str, Any] = {
        "status": "healthy" if all_healthy else "degraded",
        "application": {
            "name": settings.application.name,
            "version": settings.application.version,
            "debug": settings.application.debug,
        },
        "database": db_status,
        "qdrant": qdrant_status,
        "configuration": "loaded",
        "version": settings.application.version,
    }

    logger.debug("Health check: status={}", response["status"])
    return response


@router.get("/version")
def version_info() -> Dict[str, str]:
    """Return application version information.

    Returns:
        JSON object with version and project details.
    """
    settings = get_settings()
    return {
        "application": settings.application.name,
        "version": settings.application.version,
        "python": __import__("sys").version,
    }
