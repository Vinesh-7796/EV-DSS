"""Content Selection — filters enriched CDS documents to only semantic
ContentNodes suitable for embedding and retrieval.

Only the following node types are considered semantic content:

    paragraph, procedure, warning, note, description

All other types (tables, IDs, metadata, DBC definitions, images, etc.)
are excluded from semantic indexing.
"""

from typing import Any, Dict, List, Optional

from backend.logger import logger
from processing.models.models import ContentNode, Document

# Semantic node types that carry natural-language content worth embedding.
SEMANTIC_NODE_TYPES = frozenset({
    "paragraph",
    "procedure",
    "warning",
    "note",
    "description",
    "caption",
    "heading",
    "list",
    "code",
})

# Node types that are explicitly excluded from semantic indexing.
EXCLUDED_NODE_TYPES = frozenset({
    "table",
    "table_row",
    "table_cell",
    "worksheet",
    "spreadsheet_row",
    "spreadsheet_cell",
    "dbc_message",
    "dbc_signal",
    "image",
    "figure",
    "ocr_text",
    "formula",
    "diagram",
})


def is_semantic_node(node_type: str) -> bool:
    """Return True if *node_type* should be included in semantic indexing."""
    return node_type in SEMANTIC_NODE_TYPES


def is_excluded_node(node_type: str) -> bool:
    """Return True if *node_type* must be excluded from semantic indexing."""
    return node_type in EXCLUDED_NODE_TYPES


class ContentSelector:
    """Walks the ContentNode hierarchy of an enriched CDS Document and
    extracts only the semantic nodes suitable for embedding and retrieval.

    The selector produces a flat list of ``ContentNode`` references
    with preserved provenance (reference, parent_id, metadata).
    """

    def __init__(self, include_headings: bool = True) -> None:
        self._include_headings = include_headings

    def select(self, doc: "Document") -> List[ContentNode]:
        """Extract semantic ContentNodes from a CDS Document.

        Parameters
        ----------
        doc : Document
            An enriched CDS Document (output of the intelligence pipeline).

        Returns
        -------
        List[ContentNode]
            Flat list of semantic nodes, preserving their original order
            via depth-first traversal.
        """
        if not doc.content_nodes:
            logger.warning("ContentSelector: document {} has no content nodes", doc.source)
            return []

        selected: List[ContentNode] = []
        self._walk(doc.content_nodes, selected)
        logger.debug(
            "ContentSelector: selected {} semantic nodes from {}",
            len(selected),
            doc.source,
        )
        return selected

    def select_from_nodes(self, nodes: List[ContentNode]) -> List[ContentNode]:
        """Extract semantic nodes from a list of ContentNodes directly."""
        selected: List[ContentNode] = []
        self._walk(nodes, selected)
        return selected

    # ── Internal ────────────────────────────────

    def _walk(self, nodes: List[ContentNode], selected: List[ContentNode]) -> None:
        for node in nodes:
            ntype = self._resolve_type(node)
            if self._include(ntype):
                selected.append(node)
            children = self._resolve_children(node)
            if children:
                self._walk(children, selected)

    @staticmethod
    def _resolve_type(node: Any) -> str:
        if isinstance(node, dict):
            return node.get("type", "")
        return getattr(node, "type", "")

    @staticmethod
    def _resolve_children(node: Any) -> List[Any]:
        if isinstance(node, dict):
            return node.get("children", [])
        return list(getattr(node, "children", []))

    def _include(self, ntype: str) -> bool:
        if not ntype:
            return False
        if ntype in EXCLUDED_NODE_TYPES:
            return False
        if ntype == "heading" and not self._include_headings:
            return False
        return ntype in SEMANTIC_NODE_TYPES


def count_semantic_nodes(doc: Document) -> Dict[str, int]:
    """Count semantic node types in a document (useful for statistics)."""
    counts: Dict[str, int] = {}

    def walk(nodes: List[ContentNode]) -> None:
        for node in nodes:
            ntype = getattr(node, "type", "") if not isinstance(node, dict) else node.get("type", "")
            if is_semantic_node(ntype):
                counts[ntype] = counts.get(ntype, 0) + 1
            children = list(getattr(node, "children", [])) if not isinstance(node, dict) else node.get("children", [])
            if children:
                walk(children)

    walk(doc.content_nodes)
    return counts
