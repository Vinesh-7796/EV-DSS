"""Image file + metadata store implementation of the KnowledgeStore interface.

Stores raw image files alongside extracted OCR metadata so that
downstream modules never need to access original engineering documents.
"""

import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.logger import logger
from processing.models.models import Document, ContentNode, Reference
from processing.store.base import KnowledgeStore


class ImageStore(KnowledgeStore):
    """Persists image files and their OCR metadata for CDS Documents.

    Files are copied to ``data/store/images/{hash}.{ext}``.
    A metadata JSON entry per file is written alongside.
    """

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        self._base_dir = Path(base_dir or Path("data") / "store" / "images")
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._manifest_path = self._base_dir / "manifest.json"
        self._manifest: Dict[str, Any] = {}
        self._load_manifest()

    # ── KnowledgeStore interface ─────────────────

    def store(self, document: Document, source_id: str = "") -> str:
        if document.type != "image":
            return ""

        # Collect image info + OCR text from content_nodes
        image_entries = self._collect_image_data(document)
        if not image_entries:
            return ""

        store_ids = []
        for entry in image_entries:
            file_hash = entry.get("hash", hashlib.md5(str(entry).encode()).hexdigest()[:16])
            store_id = f"img_{file_hash}"
            meta_path = self._base_dir / f"{store_id}.json"

            meta = {
                "store_id": store_id,
                "source": document.source,
                "filename": document.metadata.filename,
                "type": "image",
                "width": entry.get("width", 0),
                "height": entry.get("height", 0),
                "format": entry.get("format", ""),
                "ocr_text": entry.get("ocr_text", ""),
                "ocr_count": entry.get("ocr_count", 0),
                "source_path": str(entry.get("source_path", "")),
                "stored_at": datetime.now().isoformat(),
            }

            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2, ensure_ascii=False)

            # Copy original file if it exists and is valid
            src_raw = entry.get("source_path", "")
            if src_raw:
                src = Path(str(src_raw))
                if src.exists() and src.is_file():
                    ext = src.suffix or ".bin"
                    dest = self._base_dir / f"{store_id}{ext}"
                    shutil.copy2(src, dest)

            self._manifest[store_id] = meta
            store_ids.append(store_id)

        self._save_manifest()
        logger.info("ImageStore: stored {} image(s) from {}", len(store_ids), document.source)
        return ",".join(store_ids)

    def retrieve(self, store_id: str) -> Optional[Document]:
        meta_path = self._base_dir / f"{store_id}.json"
        if not meta_path.exists():
            return None
        with open(meta_path) as f:
            meta = json.load(f)

        from processing.models.models import (
            Document, DocumentMetadata, ProcessingInfo, Statistics,
            ContentNode, Reference,
        )
        doc = Document(
            source=meta.get("source", store_id),
            type="image",
            metadata=DocumentMetadata(
                filename=meta.get("filename", ""),
                image_width=meta.get("width", 0),
                image_height=meta.get("height", 0),
                image_format=meta.get("format", ""),
            ),
            raw_text=meta.get("ocr_text", ""),
        )
        doc.content_nodes = [
            ContentNode(
                id=store_id,
                type="image",
                content={
                    "width": meta.get("width", 0),
                    "height": meta.get("height", 0),
                    "format": meta.get("format", ""),
                },
                reference=Reference(type="image", location={"image_region": "full"}),
            )
        ]
        return doc

    def list_documents(self) -> List[Dict[str, Any]]:
        return list(self._manifest.values())

    def delete(self, store_id: str) -> bool:
        if store_id not in self._manifest:
            return False
        meta_path = self._base_dir / f"{store_id}.json"
        if meta_path.exists():
            meta_path.unlink()
        # Also try to remove image file
        for ext in [".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".bin"]:
            img_path = self._base_dir / f"{store_id}{ext}"
            if img_path.exists():
                img_path.unlink()
                break
        del self._manifest[store_id]
        self._save_manifest()
        return True

    def health_check(self) -> bool:
        return self._base_dir.exists()

    @property
    def name(self) -> str:
        return "image"

    # ── Internal helpers ────────────────────────

    def _collect_image_data(self, document: Document) -> List[Dict[str, Any]]:
        entries: List[Dict[str, Any]] = []

        def walk(nodes: Any) -> None:
            if isinstance(nodes, list):
                for n in nodes:
                    _walk_node(n)
            elif isinstance(nodes, dict):
                _walk_node(nodes)

        def _walk_node(n: Any) -> None:
            ntype = n.get("type", "") if isinstance(n, dict) else getattr(n, "type", "")
            if ntype in ("image", "ocr_text"):
                content = n.get("content", {}) if isinstance(n, dict) else getattr(n, "content", {})
                meta = n.get("metadata", {}) if isinstance(n, dict) else getattr(n, "metadata", {})
                ref = n.get("reference", {}) if isinstance(n, dict) else getattr(n, "reference", None)
                ref_loc = {}
                if ref:
                    ref_loc = ref.get("location", {}) if isinstance(ref, dict) else getattr(ref, "location", {})
                entries.append(
                    {
                        "width": content.get("width", 0) if isinstance(content, dict) else 0,
                        "height": content.get("height", 0) if isinstance(content, dict) else 0,
                        "format": content.get("format", "") if isinstance(content, dict) else "",
                        "ocr_text": content if isinstance(content, str) else meta.get("text", ""),
                        "ocr_count": 1,
                        "source_path": ref_loc.get("path", ""),
                    }
                )
            children = n.get("children", []) if isinstance(n, dict) else getattr(n, "children", [])
            walk(children)

        walk(document.content_nodes)

        if not entries:
            entries.append(
                {
                    "width": document.metadata.image_width,
                    "height": document.metadata.image_height,
                    "format": document.metadata.image_format,
                    "ocr_text": document.raw_text,
                    "ocr_count": 1 if document.raw_text else 0,
                    "source_path": "",
                }
            )

        return entries

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
