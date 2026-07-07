"""JSON filesystem implementation of the KnowledgeStore interface.

Saves each CDS Document as a pretty-printed JSON file inside a
configurable base directory.  A manifest tracks every stored document
so that ``list_documents`` is efficient even for large collections.
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.logger import logger
from processing.models.models import Document
from processing.store.base import KnowledgeStore
class JSONKnowledgeStore(KnowledgeStore):
    """Persists CDS Documents as JSON files on the filesystem.

    ``data/store/json/{type}/{stem}.json`` + a shared ``manifest.json``.
    """

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        self._base_dir = Path(base_dir or Path("data") / "store" / "json")
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._manifest_path = self._base_dir / "manifest.json"
        self._manifest: Dict[str, Any] = {}
        self._load_manifest()

    # ── KnowledgeStore interface ─────────────────

    def store(self, document: Document, source_id: str = "") -> str:
        stem = Path(document.source).stem
        doc_type = document.type or "unknown"
        type_dir = self._base_dir / doc_type
        type_dir.mkdir(parents=True, exist_ok=True)
        out_path = type_dir / f"{stem}.json"

        data = document.to_dict()
        data["_store_id"] = source_id or stem
        data["_stored_at"] = datetime.now().isoformat()

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

        store_id = f"{doc_type}/{stem}"
        self._manifest[store_id] = {
            "store_id": store_id,
            "source": document.source,
            "type": document.type,
            "filename": document.metadata.filename,
            "file_size": document.metadata.file_size,
            "checksum": document.metadata.checksum,
            "stored_at": datetime.now().isoformat(),
        }
        self._save_manifest()
        logger.info("JSONKnowledgeStore: stored {} as {}", document.source, store_id)
        return store_id

    def retrieve(self, store_id: str) -> Optional[Document]:
        parts = store_id.split("/", 1)
        if len(parts) != 2:
            logger.warning("JSONKnowledgeStore: invalid store_id '{}'", store_id)
            return None
        doc_type, stem = parts
        out_path = self._base_dir / doc_type / f"{stem}.json"
        if not out_path.exists():
            return None
        from processing.utils.io import load_processed_document
        raw = load_processed_document(out_path)
        from processing.engine import dict_to_document
        return dict_to_document(raw)

    def list_documents(self) -> List[Dict[str, Any]]:
        return list(self._manifest.values())

    def delete(self, store_id: str) -> bool:
        if store_id not in self._manifest:
            return False
        parts = store_id.split("/", 1)
        if len(parts) == 2:
            out_path = self._base_dir / parts[0] / f"{parts[1]}.json"
            if out_path.exists():
                out_path.unlink()
        del self._manifest[store_id]
        self._save_manifest()
        return True

    def health_check(self) -> bool:
        return self._base_dir.exists()

    @property
    def name(self) -> str:
        return "json"

    # ── Internal helpers ────────────────────────

    def _load_manifest(self) -> None:
        if self._manifest_path.exists():
            try:
                with open(self._manifest_path) as f:
                    self._manifest = json.load(f)
            except (json.JSONDecodeError, OSError):
                self._manifest = {}

    def _save_manifest(self) -> None:
        with open(self._manifest_path, "w", encoding="utf-8") as f:
            json.dump(self._manifest, f, indent=2, ensure_ascii=False)
