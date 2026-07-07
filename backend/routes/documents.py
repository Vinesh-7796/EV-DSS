"""Document endpoints — list and retrieve processed documents."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter()

STORE_DIR = Path(__file__).resolve().parent.parent.parent / "ev-ddss" / "data" / "store" / "json"


class DocumentSummary(BaseModel):
    id: str = ""
    title: str = ""
    source: str = ""
    doc_type: str = ""
    sheet_count: int = 0
    content_node_count: int = 0
    edge_count: int = 0
    file_size: int = 0
    status: str = ""
    processed_at: str = ""


class DocumentDetail(BaseModel):
    id: str = ""
    title: str = ""
    source: str = ""
    doc_type: str = ""
    sheet_count: int = 0
    content_node_count: int = 0
    edge_count: int = 0
    file_size: int = 0
    status: str = ""
    processed_at: str = ""
    sections: List[Dict[str, Any]] = Field(default_factory=list)
    tables: List[Dict[str, Any]] = Field(default_factory=list)
    chunks: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


def _load_manifest() -> List[Dict[str, Any]]:
    manifest_path = STORE_DIR / "manifest.json"
    if not manifest_path.exists():
        return []
    try:
        with open(manifest_path) as f:
            data = json.load(f)
        return list(data.values())
    except Exception:
        return []


def _load_document(source: str, doc_type: str) -> Optional[Dict[str, Any]]:
    stem = Path(source).stem
    fp = STORE_DIR / doc_type / f"{stem}.json"
    if not fp.exists():
        return None
    try:
        with open(fp, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


@router.get("", response_model=List[DocumentSummary])
async def list_documents(
    doc_type: Optional[str] = Query(None, alias="type"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    entries = _load_manifest()
    if doc_type:
        entries = [e for e in entries if e.get("type") == doc_type]
    total = len(entries)
    page = entries[offset:offset + limit]

    result = []
    for entry in page:
        source = entry.get("source", "")
        dtype = entry.get("type", "")
        doc_data = _load_document(source, dtype)
        content_node_count = 0
        edge_count = 0
        sheet_count = 0
        file_size = entry.get("file_size", 0)
        if doc_data:
            rg = doc_data.get("relationship_graph", {}) or {}
            content_node_count = len(rg.get("nodes", {}))
            edge_count = len(rg.get("edges", []))
            sheet_count = len(doc_data.get("sections", []))
            file_size = doc_data.get("metadata", {}).get("file_size", 0) or file_size
        result.append(DocumentSummary(
            id=source,
            title=source,
            source=source,
            doc_type=dtype,
            sheet_count=sheet_count,
            content_node_count=content_node_count,
            edge_count=edge_count,
            file_size=file_size,
            status="indexed",
            processed_at=entry.get("stored_at", ""),
        ))
    return result


@router.get("/{document_id}", response_model=DocumentDetail)
async def get_document(document_id: str):
    for entry in _load_manifest():
        source = entry.get("source", "")
        dtype = entry.get("type", "")
        if source == document_id or Path(source).stem == document_id:
            doc_data = _load_document(source, dtype)
            if doc_data:
                rg = doc_data.get("relationship_graph", {}) or {}
                cn_count = len(rg.get("nodes", {}))
                edge_count = len(rg.get("edges", []))
                sheet_count = len(doc_data.get("sections", []))
                return DocumentDetail(
                    id=source,
                    title=source,
                    source=source,
                    doc_type=dtype,
                    sheet_count=sheet_count,
                    content_node_count=cn_count,
                    edge_count=edge_count,
                    file_size=doc_data.get("metadata", {}).get("file_size", 0),
                    status="indexed",
                    processed_at=entry.get("stored_at", ""),
                    sections=doc_data.get("sections", []),
                    tables=doc_data.get("tables", []),
                    chunks=doc_data.get("chunks", []),
                    metadata=doc_data.get("metadata", {}),
                )
    raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
