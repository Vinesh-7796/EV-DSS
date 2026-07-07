"""RelationshipGraph enrichment — adds entity-derived ContentNodes and edges

into the CDS Document's ``relationship_graph``.
"""

from typing import Any, Dict, List, Optional

from backend.logger import logger
from processing.enrichment.models import (
    CanonicalEntity,
    EntityRelationship,
    ALL_RELATIONSHIP_TYPES,
)
from processing.models.models import (
    ContentNode,
    Document,
    Edge,
    Reference,
    RelationshipGraph,
    NODE_TYPE_PARAGRAPH,
)


class GraphEnricher:
    """Adds canonical entities and discovered relationships into a CDS

    Document's ``RelationshipGraph`` and ``content_nodes``.
    """

    def __init__(self) -> None:
        self._nodes_added: int = 0
        self._edges_added: int = 0

    # ── Public API ──────────────────────────────

    def enrich(
        self,
        doc: Document,
        canonical_entities: List[CanonicalEntity],
        relationships: List[EntityRelationship],
    ) -> Document:
        """Add entities and relationships into *doc*'s CDS structures.

        Returns the enriched Document.
        """
        self._nodes_added = 0
        self._edges_added = 0

        rg = doc.relationship_graph
        if isinstance(rg, dict):
            rg = RelationshipGraph(nodes=rg.get("nodes", {}), edges=rg.get("edges", []))
            doc.relationship_graph = rg

        # Add entity nodes
        for ce in canonical_entities:
            node_id = f"enriched_{ce.id}"
            if node_id not in rg.nodes:
                cn = ContentNode(
                    id=node_id,
                    type=_entity_type_to_node_type(ce.type),
                    content=ce.canonical_name,
                    reference=Reference(
                        type="knowledge",
                        location={"entity_type": ce.type, "canonical_name": ce.canonical_name},
                    ),
                    metadata={
                        "entity_id": ce.id,
                        "aliases": ce.aliases,
                        "source_documents": ce.source_documents,
                    },
                )
                rg.nodes[node_id] = cn
                self._nodes_added += 1

            # Also add to content_nodes as an enrichment root
            if not any(c.id == node_id for c in doc.content_nodes):
                enrichment_node = ContentNode(
                    id=node_id,
                    type=_entity_type_to_node_type(ce.type),
                    content=ce.canonical_name,
                    reference=Reference(
                        type="knowledge",
                        location={"entity_type": ce.type, "canonical_name": ce.canonical_name},
                    ),
                    metadata={
                        "entity_id": ce.id,
                        "aliases": ce.aliases,
                        "source_documents": ce.source_documents,
                        "enriched": True,
                    },
                )
                doc.content_nodes.append(enrichment_node)

        # Add relationship edges
        existing_pairs: set = set()
        for edge in rg.edges:
            src = edge.source if hasattr(edge, "source") else ""
            tgt = edge.target if hasattr(edge, "target") else ""
            rt = edge.relationship_type if hasattr(edge, "relationship_type") else ""
            existing_pairs.add((src, tgt, rt))

        for rel in relationships:
            src_node = f"enriched_{rel.source_entity_id}"
            tgt_node = f"enriched_{rel.target_entity_id}"
            pair = (src_node, tgt_node, rel.relationship_type)
            if pair not in existing_pairs:
                existing_pairs.add(pair)
                rg.edges.append(Edge(
                    source=src_node,
                    target=tgt_node,
                    relationship_type=rel.relationship_type,
                    confidence=rel.confidence,
                    metadata=rel.metadata,
                ))
                self._edges_added += 1

        doc.relationship_graph = rg
        logger.info(
            "GraphEnricher: added {} nodes and {} edges",
            self._nodes_added,
            self._edges_added,
        )
        return doc

    @property
    def stats(self) -> Dict[str, int]:
        return {"nodes_added": self._nodes_added, "edges_added": self._edges_added}


# ──────────────────────────────────────────────
#  Helper
# ──────────────────────────────────────────────


def _entity_type_to_node_type(etype: str) -> str:
    mapping: Dict[str, str] = {
        "error_code": "code",
        "connector": "diagram",
        "ecu": "component",
        "can_message": "dbc_message",
        "can_signal": "dbc_signal",
        "sensor": "component",
        "relay": "component",
        "fuse": "component",
        "component": "component",
        "subsystem": "heading",
        "procedure": "procedure",
        "warning": "warning",
        "measurement": "formula",
    }
    return mapping.get(etype, "paragraph")
