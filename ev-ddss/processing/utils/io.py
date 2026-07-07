"""File I/O utilities for the document processing engine.

Handles saving processed documents as JSON and loading them back.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from backend.logger import logger
from processing.models.models import (
    ContentNode,
    Document,
    Edge,
    ProcessingInfo,
    RelationshipGraph,
    Statistics,
)


def ensure_output_dir(doc_type: str, base_dir: Optional[Path] = None) -> Path:
    """Create and return the output directory for a document type.

    Args:
        doc_type: One of 'pdf', 'excel', 'dbc', 'image'.
        base_dir: Root output directory. Defaults to data/processed.

    Returns:
        Path to the type-specific output directory.
    """
    if base_dir is None:
        base_dir = Path("data") / "processed"
    out = base_dir / doc_type
    out.mkdir(parents=True, exist_ok=True)
    return out


def save_processed_document(
    document: Document,
    output_dir: Optional[Path] = None,
) -> Path:
    """Serialize a Document to JSON and write it to disk.

    Args:
        document: The processed document to save.
        output_dir: Override the default output directory.

    Returns:
        The path to the written JSON file.
    """
    # Auto-compute CDS statistics if content_nodes are present but statistics are empty
    if document.content_nodes and document.statistics.total_content_nodes == 0:
        _compute_statistics(document)

    doc_type = document.type or "unknown"
    out_dir = ensure_output_dir(doc_type, output_dir)
    stem = Path(document.source).stem
    out_path = out_dir / f"{stem}.json"

    data = document.to_dict()
    sv = document.processing_info.schema_version if document.processing_info else "1.0"
    data["_schema_version"] = sv
    data["_generated_at"] = datetime.now().isoformat()

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    logger.info("Saved processed document: {} ({} KB)", out_path.name, out_path.stat().st_size // 1024)
    return out_path


def load_processed_document(path: Path) -> Dict[str, Any]:
    """Load a previously saved processed document from disk.

    Args:
        path: Path to the JSON file.

    Returns:
        The deserialized dictionary.
    """
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ──────────────────────────────────────────────
#  Internal helpers
# ──────────────────────────────────────────────


def _compute_statistics(doc: Document) -> None:
    """Compute and populate CDS Statistics from content_nodes."""
    type_counts: Dict[str, int] = {}
    total_nodes = 0
    max_depth = 0

    def walk(nodes: Any, depth: int = 0) -> None:
        nonlocal total_nodes, max_depth
        if isinstance(nodes, list):
            for n in nodes:
                _walk_node(n, depth)
        elif isinstance(nodes, dict):
            _walk_node(nodes, depth)

    def _walk_node(n: Any, depth: int) -> None:
        nonlocal total_nodes, max_depth
        total_nodes += 1
        max_depth = max(max_depth, depth)
        ntype = n.get("type", "unknown") if isinstance(n, dict) else getattr(n, "type", "unknown")
        type_counts[ntype] = type_counts.get(ntype, 0) + 1
        children = n.get("children", []) if isinstance(n, dict) else getattr(n, "children", [])
        walk(children, depth + 1)

    # Walk root nodes (could be dataclass instances or dicts from JSON load)
    walk(doc.content_nodes)

    edge_count = 0
    rg = doc.relationship_graph
    if hasattr(rg, "edges") and isinstance(rg.edges, list):
        edge_count = len(rg.edges)
    elif isinstance(rg, dict):
        edge_count = len(rg.get("edges", []))

    doc.statistics.total_content_nodes = total_nodes
    doc.statistics.total_relationships = edge_count
    doc.statistics.node_type_counts = type_counts
    doc.statistics.max_depth = max_depth
