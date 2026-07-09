import asyncio
import time
from collections import deque
from typing import Any, Deque, Dict

import httpx
from fastapi import APIRouter

from config import get_settings

router = APIRouter()

# Rolling window of recent response times (ms)
_response_times: Deque[float] = deque(maxlen=50)


def record_response_time(ms: float) -> None:
    """Called by the AI service after each diagnosis to track avg latency."""
    _response_times.append(ms)


def _avg_response_time() -> float:
    if not _response_times:
        return 0.0
    return round(sum(_response_times) / len(_response_times), 1)


async def _probe_url(url: str, label: str) -> Dict[str, Any]:
    """Async HTTP probe — resolves in ≤1.5s."""
    try:
        async with httpx.AsyncClient(timeout=1.5) as client:
            resp = await client.get(url)
        if resp.status_code == 200:
            return {"status": "healthy", "url": url}
        return {"status": "degraded", "url": url, "code": resp.status_code}
    except Exception as exc:
        return {"status": "offline", "url": url, "error": str(exc)[:80]}


def _count_indexed_docs() -> Dict[str, int]:
    """Read manifest.json to count docs, chunks and graph entities."""
    import json
    from pathlib import Path
    store_dir = (
        Path(__file__).resolve().parent.parent.parent / "ev-ddss" / "data" / "store" / "json"
    )
    manifest_path = store_dir / "manifest.json"
    if not manifest_path.exists():
        return {"indexed_documents": 0, "total_chunks": 0, "total_entities": 0, "last_update": ""}

    try:
        with open(manifest_path) as f:
            manifest = json.load(f)

        total_chunks = 0
        total_entities = 0
        last_update = ""

        for store_id, entry in manifest.items():
            source = entry.get("source", "")
            doc_type = entry.get("type", "unknown")
            stem = Path(source).stem
            doc_path = store_dir / doc_type / f"{stem}.json"
            stored_at = entry.get("stored_at", "")
            if stored_at > last_update:
                last_update = stored_at

            if doc_path.exists():
                try:
                    with open(doc_path, encoding="utf-8") as f:
                        doc = json.load(f)
                    total_chunks += len(doc.get("chunks", []))
                    rg = doc.get("relationship_graph", {}) or {}
                    total_entities += len(rg.get("nodes", {}))
                except Exception:
                    pass

        return {
            "indexed_documents": len(manifest),
            "total_chunks": total_chunks,
            "total_entities": total_entities,
            "last_update": last_update,
        }
    except Exception:
        return {"indexed_documents": 0, "total_chunks": 0, "total_entities": 0, "last_update": ""}


def _get_gpu_info() -> Dict[str, Any]:
    """Attempt to detect GPU availability."""
    # Try torch first
    try:
        import torch
        if torch.cuda.is_available():
            name = torch.cuda.get_device_name(0)
            vram = torch.cuda.get_device_properties(0).total_memory // (1024 ** 2)
            return {"available": True, "name": name, "vram_mb": vram}
    except ImportError:
        pass

    # Fallback: hard-coded from known machine spec
    import subprocess
    try:
        res = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=3
        )
        if res.returncode == 0:
            parts = res.stdout.strip().split(",")
            return {
                "available": True,
                "name": parts[0].strip() if parts else "Unknown",
                "vram_mb": int(parts[1].strip()) if len(parts) > 1 else 0,
            }
    except Exception:
        pass

    return {"available": False, "name": None, "vram_mb": 0}


def _get_ram_info() -> Dict[str, Any]:
    """Return RAM usage via psutil (optional)."""
    try:
        import psutil
        vm = psutil.virtual_memory()
        return {
            "total_gb": round(vm.total / (1024 ** 3), 1),
            "used_gb": round(vm.used / (1024 ** 3), 1),
            "available_gb": round(vm.available / (1024 ** 3), 1),
            "percent": vm.percent,
        }
    except ImportError:
        return {"available": False}
    except Exception:
        return {"available": False}


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Comprehensive system status for the Settings → System Status panel."""
    settings = get_settings()

    # Probe Ollama and Qdrant concurrently
    ollama_info, qdrant_info = await asyncio.gather(
        _probe_url(settings.reasoning.ollama_url, "Ollama"),
        _probe_url(settings.qdrant.url.rstrip("/") + "/", "Qdrant"),
    )
    kb_counts = _count_indexed_docs()
    gpu_info = _get_gpu_info()
    ram_info = _get_ram_info()

    # KB watcher status (non-critical)
    try:
        from services.kb_watcher import get_kb_watcher
        kb_status = get_kb_watcher().status()
        kb_watcher_running = kb_status.watcher_running
    except Exception:
        kb_watcher_running = False

    # Overall status
    overall = "healthy"

    return {
        "status": overall,
        "components": {
            "backend": {
                "status": "healthy",
                "name": settings.application.name,
                "version": settings.application.version,
            },
            "ollama": {
                **ollama_info,
                "active_model": settings.reasoning.model,
                "runtime": settings.reasoning.runtime,
            },
            "embedding": {
                "status": "configured",
                "model": settings.retrieval.embedding_model,
                "dimension": settings.retrieval.embedding_dimension,
            },
            "vector_db": qdrant_info,
            "graph": {
                "status": "healthy" if kb_counts["total_entities"] > 0 else "empty",
                "entity_count": kb_counts["total_entities"],
            },
            "knowledge_base": {
                "status": "healthy" if kb_counts["indexed_documents"] > 0 else "empty",
                "indexed_documents": kb_counts["indexed_documents"],
                "total_chunks": kb_counts["total_chunks"],
                "total_entities": kb_counts["total_entities"],
                "last_update": kb_counts["last_update"],
                "watcher_running": kb_watcher_running,
            },
        },
        "performance": {
            "avg_response_time_ms": _avg_response_time(),
            "response_samples": len(_response_times),
        },
        "hardware": {
            "gpu": gpu_info,
            "ram": ram_info,
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
