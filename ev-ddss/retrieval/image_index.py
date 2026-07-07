"""Image Index — OCR-based retrieval over stored engineering images.

Provides text search over OCR-extracted text and metadata filtering
for images stored by the ``ImageStore``.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.logger import logger
from config import get_settings


class ImageIndex:
    """OCR-based image retrieval index.

    Searches over the image metadata JSON files produced by
    ``ImageStore`` for OCR text matches and image metadata
    filtering.

    The index is built lazily from the ``ImageStore`` manifest
    and metadata files.
    """

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        settings = get_settings()
        self._base_dir = Path(base_dir or settings.store.image_path)
        self._manifest_path = self._base_dir / "manifest.json"
        self._entries: List[Dict[str, Any]] = []
        self._loaded = False

    # ── Build / Load ────────────────────────────

    def load(self) -> bool:
        """Load image metadata entries from the manifest and JSON files."""
        self._entries = []

        if not self._base_dir.exists():
            logger.warning("ImageIndex: base directory does not exist: {}", self._base_dir)
            return False

        # Load from manifest first
        if self._manifest_path.exists():
            try:
                with open(self._manifest_path) as f:
                    manifest = json.load(f)
                for store_id, meta in manifest.items():
                    self._entries.append(meta)
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("ImageIndex: manifest load failed: {}", exc)

        # Also load individual metadata files for OCR text
        for meta_file in self._base_dir.glob("img_*.json"):
            if meta_file.name == "manifest.json":
                continue
            store_id = meta_file.stem
            already = any(e.get("store_id") == store_id for e in self._entries)
            if not already:
                try:
                    with open(meta_file) as f:
                        self._entries.append(json.load(f))
                except (json.JSONDecodeError, OSError):
                    pass

        self._loaded = True
        logger.debug("ImageIndex: loaded {} image entries from {}", len(self._entries), self._base_dir)
        return True

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def count(self) -> int:
        return len(self._entries)

    # ── Search ──────────────────────────────────

    def search_by_ocr(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search images by OCR text content (case-insensitive substring).

        Parameters
        ----------
        query : str
            Search query text.
        top_k : int
            Maximum results.

        Returns
        -------
        list of dict
            Each entry has keys: ``store_id``, ``source``, ``filename``,
            ``ocr_text``, ``score`` (based on term frequency), ``width``,
            ``height``, ``format``.
        """
        if not self._loaded:
            self.load()

        q_lower = query.lower()
        scored: List[Dict[str, Any]] = []

        for entry in self._entries:
            ocr_text = entry.get("ocr_text", "") or ""
            if not ocr_text:
                continue

            ocr_lower = ocr_text.lower()
            if q_lower in ocr_lower:
                # Simple relevance score: term frequency / text length
                tf = ocr_lower.count(q_lower)
                score = tf / max(len(ocr_lower), 1) * 100.0
                scored.append({
                    "store_id": entry.get("store_id", ""),
                    "source": entry.get("source", ""),
                    "filename": entry.get("filename", ""),
                    "ocr_text": ocr_text[:500],
                    "score": round(min(score, 1.0), 4),
                    "width": entry.get("width", 0),
                    "height": entry.get("height", 0),
                    "format": entry.get("format", ""),
                })

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    def search_by_metadata(
        self,
        filters: Dict[str, Any],
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """Filter images by metadata fields (exact match).

        Supported filters: ``source``, ``filename``, ``format``.
        """
        if not self._loaded:
            self.load()

        results = []
        for entry in self._entries:
            match = True
            for key, val in filters.items():
                if entry.get(key) != val:
                    match = False
                    break
            if match:
                results.append(entry)
                if len(results) >= top_k:
                    break

        return results

    def get_all(self) -> List[Dict[str, Any]]:
        """Return all indexed image entries."""
        if not self._loaded:
            self.load()
        return list(self._entries)

    def health_check(self) -> bool:
        return self._base_dir.exists()
