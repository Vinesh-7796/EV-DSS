"""Chunk Optimization — transforms selected semantic ContentNodes into
optimised chunks suitable for embedding and retrieval.

Strategies
──────────

* Merge adjacent small semantic nodes (e.g. short paragraphs, list items)
  up to a configurable token limit.
* Split oversized nodes at natural boundaries (sentence, paragraph).
* Preserve full provenance (section title, page number, source document)
  so each chunk remains self-describing.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from backend.logger import logger
from config import get_settings
from processing.models.models import ContentNode


@dataclass
class Chunk:
    """An atomic retrieval unit produced by the chunk optimizer."""

    chunk_id: str = ""
    text: str = ""
    node_type: str = ""
    source: str = ""
    document_id: str = ""
    section_title: str = ""
    chapter: str = ""
    page_number: int = 0
    parent_id: Optional[str] = None
    original_node_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    reference: Optional[Dict[str, Any]] = None


# Simple tokenisation approximation (characters per token ≈ 4 for English).
_CHARS_PER_TOKEN = 4.0


def _estimate_tokens(text: str) -> int:
    return max(1, round(len(text) / _CHARS_PER_TOKEN))


def _split_sentences(text: str) -> List[str]:
    """Split text into sentences (naive but fast)."""
    parts = re.split(r"(?<=[.?!])\s+", text.strip())
    return [p for p in parts if p]


class ChunkOptimizer:
    """Optimises semantic ContentNodes into chunks for embedding.

    Parameters
    ----------
    chunk_size : int
        Target chunk size in tokens (default from config).
    chunk_overlap : int
        Overlap between adjacent chunks in tokens (default from config).
    min_chunk_tokens : int
        Minimum chunk size; smaller nodes are merged forward.
    """

    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        min_chunk_tokens: int = 32,
    ) -> None:
        settings = get_settings().retrieval
        self._chunk_size = chunk_size or settings.chunk_size
        self._chunk_overlap = chunk_overlap or settings.chunk_overlap
        self._min_chunk_tokens = min_chunk_tokens
        self._counter = 0

    def optimize(self, nodes: List[ContentNode], source: str = "", document_id: str = "") -> List[Chunk]:
        """Convert a list of semantic ContentNodes into optimised chunks.

        Parameters
        ----------
        nodes : List[ContentNode]
            Semantic nodes from the ``ContentSelector``.
        source : str
            Source document name (e.g. filename).
        document_id : str
            Store identifier of the source document.

        Returns
        -------
        List[Chunk]
            Optimised chunks ready for embedding.
        """
        self._counter = 0
        if not nodes:
            return []

        # Phase 1 — extract text with provenance from each node
        entries: List[_NodeEntry] = []
        for node in nodes:
            text = self._extract_text(node)
            if not text:
                continue
            entries.append(
                _NodeEntry(
                    text=text,
                    node_id=self._resolve_id(node),
                    node_type=self._resolve_type(node),
                    parent_id=self._resolve_parent_id(node),
                    page_number=self._resolve_page(node),
                    section_title=self._resolve_section_title(node),
                    metadata=self._resolve_metadata(node),
                    reference=self._resolve_reference(node),
                )
            )

        if not entries:
            return []

        # Phase 2 — merge small entries, split large entries
        merged = self._merge_small(entries)
        chunks: List[Chunk] = []
        for entry in merged:
            estimated = _estimate_tokens(entry.text)
            if estimated <= self._chunk_size:
                chunks.append(self._entry_to_chunk(entry, source, document_id))
            else:
                chunks.extend(self._split_large(entry, source, document_id))

        logger.debug(
            "ChunkOptimizer: {} nodes → {} chunks (size={}, overlap={})",
            len(nodes),
            len(chunks),
            self._chunk_size,
            self._chunk_overlap,
        )
        return chunks

    # ── Internal helpers ────────────────────────

    def _next_id(self) -> str:
        self._counter += 1
        return f"CHUNK{self._counter:05d}"

    @staticmethod
    def _extract_text(node: ContentNode) -> str:
        content = node.content if hasattr(node, "content") else (node.get("content", "") if isinstance(node, dict) else "")
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, dict):
            return content.get("text", "") or content.get("value", "") or str(content)
        return str(content).strip()

    @staticmethod
    def _resolve_id(node: Any) -> str:
        return node.id if hasattr(node, "id") else (node.get("id", "") if isinstance(node, dict) else "")

    @staticmethod
    def _resolve_type(node: Any) -> str:
        return node.type if hasattr(node, "type") else (node.get("type", "") if isinstance(node, dict) else "")

    @staticmethod
    def _resolve_parent_id(node: Any) -> Optional[str]:
        val = node.parent_id if hasattr(node, "parent_id") else (node.get("parent_id") if isinstance(node, dict) else None)
        return val

    @staticmethod
    def _resolve_page(node: Any) -> int:
        ref = node.reference if hasattr(node, "reference") else (node.get("reference") if isinstance(node, dict) else None)
        if ref:
            loc = ref.location if hasattr(ref, "location") else (ref.get("location", {}) if isinstance(ref, dict) else {})
            return loc.get("page", 0) or 0
        return 0

    @staticmethod
    def _resolve_section_title(node: Any) -> str:
        meta = node.metadata if hasattr(node, "metadata") else (node.get("metadata", {}) if isinstance(node, dict) else {})
        if isinstance(meta, dict):
            return meta.get("section_title", "") or meta.get("heading", "") or ""
        return getattr(meta, "section_title", "") or getattr(meta, "heading", "") or ""

    @staticmethod
    def _resolve_metadata(node: Any) -> Dict[str, Any]:
        if isinstance(node, dict):
            return {k: v for k, v in node.get("metadata", {}).items() if k != "children"}
        return {k: v for k, v in getattr(node, "metadata", {}).items() if k != "children"}

    @staticmethod
    def _resolve_reference(node: Any) -> Optional[Dict[str, Any]]:
        ref = node.reference if hasattr(node, "reference") else (node.get("reference") if isinstance(node, dict) else None)
        if ref is None:
            return None
        if hasattr(ref, "type"):
            return {"type": ref.type, "location": ref.location if hasattr(ref, "location") else {}}
        if isinstance(ref, dict):
            return dict(ref)
        return None

    def _entry_to_chunk(self, entry: "_NodeEntry", source: str, document_id: str) -> Chunk:
        cid = self._next_id()
        return Chunk(
            chunk_id=cid,
            text=entry.text,
            node_type=entry.node_type,
            source=source or "",
            document_id=document_id or "",
            section_title=entry.section_title,
            page_number=entry.page_number,
            parent_id=entry.parent_id,
            original_node_ids=[entry.node_id] if entry.node_id else [],
            metadata=entry.metadata,
            reference=entry.reference,
        )

    def _merge_small(self, entries: List["_NodeEntry"]) -> List["_NodeEntry"]:
        """Merge consecutive entries whose combined token count is below
        ``min_chunk_tokens``."""
        if not entries:
            return []
        merged: List[_NodeEntry] = []
        buffer = entries[0]
        for entry in entries[1:]:
            combined_tokens = _estimate_tokens(buffer.text) + _estimate_tokens(entry.text)
            if combined_tokens <= self._chunk_size and _estimate_tokens(buffer.text) < self._min_chunk_tokens:
                buffer = _NodeEntry(
                    text=buffer.text + "\n\n" + entry.text,
                    node_id=buffer.node_id or entry.node_id,
                    node_type=buffer.node_type or entry.node_type,
                    parent_id=buffer.parent_id or entry.parent_id,
                    page_number=buffer.page_number or entry.page_number,
                    section_title=buffer.section_title or entry.section_title,
                    metadata={**buffer.metadata, **entry.metadata},
                    reference=buffer.reference or entry.reference,
                )
            else:
                merged.append(buffer)
                buffer = entry
        merged.append(buffer)
        return merged

    def _split_large(self, entry: "_NodeEntry", source: str, document_id: str) -> List[Chunk]:
        """Split a single large entry into multiple chunks at sentence
        boundaries."""
        sentences = _split_sentences(entry.text)
        if len(sentences) <= 1:
            return [self._entry_to_chunk(entry, source, document_id)]

        chunks: List[Chunk] = []
        current_parts: List[str] = []
        current_tokens = 0

        for sentence in sentences:
            sent_tokens = _estimate_tokens(sentence)
            if current_tokens + sent_tokens > self._chunk_size and current_parts:
                text = " ".join(current_parts)
                sub_entry = _NodeEntry(
                    text=text,
                    node_id=entry.node_id,
                    node_type=entry.node_type,
                    parent_id=entry.parent_id,
                    page_number=entry.page_number,
                    section_title=entry.section_title,
                    metadata=entry.metadata,
                    reference=entry.reference,
                )
                chunks.append(self._entry_to_chunk(sub_entry, source, document_id))
                # Overlap: keep last sentences for continuity
                overlap_tokens = 0
                overlap_parts: List[str] = []
                for s in reversed(current_parts):
                    st = _estimate_tokens(s)
                    if overlap_tokens + st > self._chunk_overlap:
                        break
                    overlap_parts.insert(0, s)
                    overlap_tokens += st
                current_parts = overlap_parts
                current_tokens = overlap_tokens

            current_parts.append(sentence)
            current_tokens += sent_tokens

        if current_parts:
            text = " ".join(current_parts)
            sub_entry = _NodeEntry(
                text=text,
                node_id=entry.node_id,
                node_type=entry.node_type,
                parent_id=entry.parent_id,
                page_number=entry.page_number,
                section_title=entry.section_title,
                metadata=entry.metadata,
                reference=entry.reference,
            )
            chunks.append(self._entry_to_chunk(sub_entry, source, document_id))

        return chunks


@dataclass
class _NodeEntry:
    """Internal representation of a parsed ContentNode for chunking."""

    text: str = ""
    node_id: str = ""
    node_type: str = ""
    parent_id: Optional[str] = None
    page_number: int = 0
    section_title: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    reference: Optional[Dict[str, Any]] = None
