"""Knowledge Base REST endpoints.

Provides API access to the KB watcher, document list, ingestion log,
manual re-index triggers, and document deletion.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel

from services.kb_watcher import get_kb_watcher

router = APIRouter()


@router.get("/raw-path")
def kb_raw_path() -> dict:
    """Return the absolute filesystem path of the raw documents folder."""
    from services.kb_watcher import get_kb_watcher
    raw_dir = get_kb_watcher()._raw_dir
    return {"path": str(raw_dir.resolve())}


@router.post("/open-folder")
def kb_open_folder() -> dict:
    """Open the raw documents folder in default platform explorer."""
    import os
    import subprocess
    import sys
    from services.kb_watcher import get_kb_watcher
    raw_dir = get_kb_watcher()._raw_dir.resolve()
    if not raw_dir.exists():
        raise HTTPException(status_code=404, detail="Raw documents folder does not exist")
    try:
        if os.name == 'nt':
            subprocess.Popen(["explorer", str(raw_dir)])
        elif sys.platform == 'darwin':
            subprocess.Popen(["open", str(raw_dir)])
        else:
            subprocess.Popen(["xdg-open", str(raw_dir)])
        return {"success": True}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))



# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ReindexRequest(BaseModel):
    filename: str


class DeleteDocumentResponse(BaseModel):
    success: bool
    message: str


class FullRefreshResponse(BaseModel):
    queued: int
    message: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/status")
def kb_status() -> Dict[str, Any]:
    """Return current KB watcher status."""
    return get_kb_watcher().status().to_dict()


@router.get("/log")
def kb_log(limit: int = Query(50, ge=1, le=200)) -> List[Dict[str, Any]]:
    """Return recent ingestion log entries."""
    return get_kb_watcher().get_log(limit=limit)


@router.get("/documents")
def kb_documents() -> List[Dict[str, Any]]:
    """Return rich document list with chunks, nodes, status, hash."""
    return get_kb_watcher().list_documents()


@router.post("/refresh")
async def kb_refresh(background_tasks: BackgroundTasks) -> FullRefreshResponse:
    """Queue all raw documents for re-indexing."""
    watcher = get_kb_watcher()
    count = watcher.queue_full_refresh()
    return FullRefreshResponse(
        queued=count,
        message=f"Queued {count} document(s) for re-indexing",
    )


@router.post("/reindex/{filename:path}")
async def kb_reindex_document(filename: str) -> Dict[str, Any]:
    """Queue a single document for re-indexing."""
    watcher = get_kb_watcher()
    ok = watcher.queue_reindex(filename)
    if not ok:
        raise HTTPException(
            status_code=404,
            detail=f"File '{filename}' not found in raw documents folder",
        )
    return {"success": True, "message": f"Queued '{filename}' for re-indexing"}


@router.delete("/documents/{filename:path}")
async def kb_delete_document(filename: str) -> DeleteDocumentResponse:
    """Remove a document from the knowledge base and its indexes."""
    watcher = get_kb_watcher()
    ok = watcher.remove_document(filename)
    if ok:
        return DeleteDocumentResponse(
            success=True,
            message=f"'{filename}' removed from knowledge base",
        )
    raise HTTPException(
        status_code=500,
        detail=f"Failed to remove '{filename}' from knowledge base",
    )
