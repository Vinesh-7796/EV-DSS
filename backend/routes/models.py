"""Model management REST endpoints.
Supports model discovery, pulling new models via Ollama (progress stream),
and switching model runtimes dynamically.
"""

import json
from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from services.model_manager import get_model_manager
from config import get_settings

router = APIRouter()

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class ActivateModelRequest(BaseModel):
    model_name: str

class PullModelRequest(BaseModel):
    model_name: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("")
def list_models() -> List[Dict[str, Any]]:
    """List all installed Ollama models with recommendation labels."""
    return get_model_manager().list_installed_models()


@router.get("/active")
def get_active_model() -> Dict[str, Any]:
    """Get the currently configured active model and runtime details."""
    settings = get_settings()
    manager = get_model_manager()
    installed = manager.list_installed_models()
    
    active_name = settings.reasoning.model
    # Find matching model details if available
    active_detail = next((m for m in installed if m["name"] == active_name), None)
    
    return {
        "active_model": active_name,
        "runtime": settings.reasoning.runtime,
        "details": active_detail,
        "ollama_url": settings.reasoning.ollama_url
    }


@router.post("/activate")
def activate_model(request: ActivateModelRequest) -> Dict[str, Any]:
    """Verify and switch the active model runtime configuration."""
    manager = get_model_manager()
    success = manager.activate_model(request.model_name)
    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to activate model '{request.model_name}'. Verify that it is downloaded and Ollama is healthy."
        )
    return {
        "success": True,
        "message": f"Successfully activated model '{request.model_name}'",
        "active_model": request.model_name
    }


@router.post("/pull")
def pull_model(request: PullModelRequest) -> StreamingResponse:
    """Download a new model from Ollama registry. Streams progress via Server-Sent Events (SSE)."""
    manager = get_model_manager()
    
    def event_generator():
        for chunk in manager.pull_model_stream(request.model_name):
            yield f"data: {chunk}\n\n"
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/hardware-recommendations")
def get_hardware_recommendations() -> Dict[str, Any]:
    """Retrieve recommended models based on current hardware specifications."""
    return get_model_manager().get_hardware_info()
