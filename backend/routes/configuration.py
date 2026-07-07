"""Configuration endpoint — expose current settings."""

from typing import Any, Dict

from fastapi import APIRouter

from config import get_settings

router = APIRouter()


@router.get("/config")
def get_config() -> Dict[str, Any]:
    settings = get_settings()
    return {
        "application": {
            "name": settings.application.name,
            "version": settings.application.version,
            "debug": settings.application.debug,
        },
        "reasoning": {
            "runtime": settings.reasoning.runtime,
            "model": settings.reasoning.model,
            "temperature": settings.reasoning.temperature,
            "max_tokens": settings.reasoning.max_tokens,
        },
        "retrieval": {
            "top_k_vector": settings.retrieval.top_k_vector,
            "top_k_graph": settings.retrieval.top_k_graph,
        },
    }


@router.get("/statistics")
def get_statistics() -> Dict[str, Any]:
    return {
        "documents_processed": 0,
        "content_nodes": 0,
        "edges": 0,
        "total_diagnostics": 0,
        "average_confidence": 0.0,
    }
