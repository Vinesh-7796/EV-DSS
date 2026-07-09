"""CDS validation for the Document Processing Engine.

Validates a Document's CDS fields before serialization:

- Required field presence
- Reference integrity
- Relationship integrity
- Parent-child hierarchy
- Deterministic IDs
- Document completeness
- Serialization roundtrip
- Duplicate detection
"""

import json
from typing import Any, Dict, List, Optional, Set

from processing.models.models import (
    ContentNode,
    Document,
    Edge,
    RelationshipGraph,
)


def _node_id(node: Any) -> str:
    """Get the ID from a ContentNode (dataclass or dict)."""
    return node.id if hasattr(node, "id") else (node.get("id", "") if isinstance(node, dict) else "")


def _node_type(node: Any) -> str:
    """Get the type from a ContentNode (dataclass or dict)."""
    return node.type if hasattr(node, "type") else (node.get("type", "") if isinstance(node, dict) else "")


def _node_children(node: Any) -> List[Any]:
    """Get children from a ContentNode (dataclass or dict)."""
    if hasattr(node, "children"):
        return list(node.children)
    if isinstance(node, dict):
        return list(node.get("children", []))
    return []


def _node_parent_id(node: Any) -> Optional[str]:
    """Get parent_id from a ContentNode (dataclass or dict)."""
    if hasattr(node, "parent_id"):
        return node.parent_id
    if isinstance(node, dict):
        return node.get("parent_id")
    return None


def _node_reference(node: Any) -> Any:
    """Get reference from a ContentNode (dataclass or dict)."""
    if hasattr(node, "reference"):
        return node.reference
    if isinstance(node, dict):
        return node.get("reference")
    return None


def _node_content(node: Any) -> Any:
    """Get content from a ContentNode (dataclass or dict)."""
    if hasattr(node, "content"):
        return node.content
    if isinstance(node, dict):
        return node.get("content")
    return ""


class ValidationError(Exception):
    """Raised when CDS validation fails."""


def validate_document(doc: Document) -> List[str]:
    """Run all validation checks and return a list of issues (empty = valid)."""
    issues: List[str] = []
    issues.extend(_validate_required_fields(doc))
    if not issues:
        issues.extend(_validate_reference_integrity(doc))
        issues.extend(_validate_relationship_integrity(doc))
        issues.extend(_validate_hierarchy(doc))
        issues.extend(_validate_ids(doc))
        issues.extend(_validate_completeness(doc))
        issues.extend(_validate_serialization(doc))
        issues.extend(_validate_duplicate_detection(doc))
    return issues


def assert_valid(doc: Document) -> None:
    """Raise ValidationError if the document fails any validation check."""
    issues = validate_document(doc)
    if issues:
        raise ValidationError("\n".join(issues))


# ──────────────────────────────────────────────
#  Internal checks
# ──────────────────────────────────────────────


def _validate_required_fields(doc: Document) -> List[str]:
    issues: List[str] = []
    if not doc.source:
        issues.append("Document.source is empty")
    if not doc.type:
        issues.append("Document.type is empty")
    return issues


def _collect_node_ids(nodes: List[Any]) -> Set[str]:
    ids: Set[str] = set()
    for n in nodes:
        nid = _node_id(n)
        if nid:
            ids.add(nid)
        ids.update(_collect_node_ids(_node_children(n)))
    return ids


def _collect_nodes_flat(nodes: List[Any]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for n in nodes:
        nid = _node_id(n)
        if nid:
            result[nid] = n
        result.update(_collect_nodes_flat(_node_children(n)))
    return result


def _validate_reference_integrity(doc: Document) -> List[str]:
    issues: List[str] = []
    all_nodes = _collect_nodes_flat(doc.content_nodes)
    for node_id, node in all_nodes.items():
        ref = _node_reference(node)
        if ref is not None:
            ref_type = ref.type if hasattr(ref, "type") else (ref.get("type", "") if isinstance(ref, dict) else "")
            if not ref_type:
                issues.append(f"ContentNode '{node_id}' has a Reference without a type")
    return issues


def _validate_relationship_integrity(doc: Document) -> List[str]:
    issues: List[str] = []
    all_ids = _collect_node_ids(doc.content_nodes)
    graph = doc.relationship_graph
    edges = graph.edges if hasattr(graph, "edges") else []
    for edge in edges:
        src = edge.source if hasattr(edge, "source") else ""
        tgt = edge.target if hasattr(edge, "target") else ""
        rtype = edge.relationship_type if hasattr(edge, "relationship_type") else ""
        if src and src not in all_ids:
            issues.append(f"Edge source '{src}' not found in content_nodes")
        if tgt and tgt not in all_ids:
            issues.append(f"Edge target '{tgt}' not found in content_nodes")
        if not rtype:
            issues.append(f"Edge ({src} -> {tgt}) missing relationship_type")
    return issues


def _validate_hierarchy(doc: Document) -> List[str]:
    issues: List[str] = []
    all_nodes = _collect_nodes_flat(doc.content_nodes)
    for node_id, node in all_nodes.items():
        pid = _node_parent_id(node)
        if pid is not None:
            if pid not in all_nodes:
                issues.append(
                    f"ContentNode '{node_id}' references non-existent parent '{pid}'"
                )
        for child in _node_children(node):
            child_pid = _node_parent_id(child)
            child_id = _node_id(child)
            if child_pid is not None and child_pid != node_id:
                issues.append(
                    f"ContentNode '{child_id}' has parent_id='{child_pid}' "
                    f"but is in children of '{node_id}'"
                )
    return issues


def _validate_ids(doc: Document) -> List[str]:
    issues: List[str] = []
    all_nodes = _collect_nodes_flat(doc.content_nodes)
    seen: Set[str] = set()
    for node_id in all_nodes:
        if not node_id:
            issues.append("ContentNode has empty id")
        elif node_id in seen:
            issues.append(f"Duplicate ContentNode id: '{node_id}'")
        seen.add(node_id)
    if not seen and doc.content_nodes:
        issues.append("ContentNodes exist but all have empty ids")
    return issues


def _validate_completeness(doc: Document) -> List[str]:
    issues: List[str] = []
    if not doc.content_nodes and not doc.raw_text:
        issues.append("Document has no content_nodes and no raw_text")
    return issues


# ──────────────────────────────────────────────
#  Enhanced validators
# ──────────────────────────────────────────────


def _validate_serialization(doc: Document) -> List[str]:
    """Verify that the Document round-trips through JSON serialisation

    without data loss — serialize to dict, serialize to JSON string,
    parse back, and compare critical fields.
    """
    issues: List[str] = []
    try:
        data = doc.to_dict()
        json_str = json.dumps(data, indent=2, ensure_ascii=False, default=str)
        roundtripped = json.loads(json_str)

        for key in ("source", "type"):
            if data.get(key) != roundtripped.get(key):
                issues.append(
                    f"Serialization roundtrip changed '{key}': "
                    f"'{data.get(key)}' -> '{roundtripped.get(key)}'"
                )
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        issues.append(f"Serialization roundtrip failed: {exc}")
    return issues


def _validate_duplicate_detection(doc: Document) -> List[str]:
    """Check for duplicate content within the document — identical node

    content at the same hierarchy level may indicate extraction errors.
    """
    issues: List[str] = []
    seen_contents: Dict[str, List[str]] = {}

    def walk(nodes: List[Any], depth: int) -> None:
        for node in nodes:
            content = _node_content(node)
            ntype = _node_type(node)
            nid = _node_id(node)
            
            # Skip row and cell nodes which naturally contain duplicate values/headers
            if ntype in ("spreadsheet_row", "spreadsheet_cell", "table_row", "table_cell", "row", "cell"):
                walk(_node_children(node), depth + 1)
                continue
                
            text_content = str(content)[:200] if content else ""
            if text_content and len(text_content) > 20:
                key = f"{ntype}::depth{depth}"
                if key not in seen_contents:
                    seen_contents[key] = []
                if text_content in seen_contents[key]:
                    issues.append(
                        f"Duplicate content in {ntype} at depth {depth}: "
                        f"'{text_content[:60]}...' (node '{nid}')"
                    )
                seen_contents[key].append(text_content)
            walk(_node_children(node), depth + 1)

    walk(doc.content_nodes, 0)
    return issues
