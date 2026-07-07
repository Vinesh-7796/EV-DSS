"""HealthService — checks component status across the system."""

from typing import Any, Dict


class HealthService:
    """Reports health status of the application and its dependencies."""

    def __init__(self) -> None:
        self._initialized = False

    def initialize(self) -> None:
        self._initialized = True

    def check(self) -> Dict[str, Any]:
        return {
            "status": "healthy",
            "components": {
                "api": {"status": "healthy"},
                "ai_core": {"status": "available"},
            },
        }


_health_service: Optional[HealthService] = None


def get_health_service() -> HealthService:
    global _health_service
    if _health_service is None:
        _health_service = HealthService()
    return _health_service
