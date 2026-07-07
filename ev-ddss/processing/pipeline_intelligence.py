"""Document Intelligence Pipeline — the top-level orchestrator.

Transforms engineering documents into validated, persisted Canonical
Document Schema (CDS) objects.

Pipeline stages
───────────────

    Document → Processor Selection → Native Parsing → CDS Transformation
    → Structural Validation → Reference Generation → RelationshipGraph
    Construction → Serialization → Knowledge Store → Processing Report

Every stage is independent and can be used separately.  The pipeline
merely chains them together.
"""

import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.logger import logger
from ingestion.models import Document as IngestionDocument
from processing.engine import ProcessingEngine
from processing.models.models import (
    ContentNode,
    Document,
    Edge,
    ProcessingInfo,
    Reference,
    RelationshipGraph,
    Statistics,
)
from processing.report import ProcessingReport
from processing.store.manager import KnowledgeStoreManager
from processing.validation import assert_valid, validate_document


class DocumentIntelligencePipeline:
    """End-to-end pipeline for engineering document intelligence.

    Usage::

        pipeline = DocumentIntelligencePipeline()
        pipeline.ingestion_setup(...)
        report = pipeline.process(ingestion_doc)
        print(report.summary())
    """

    def __init__(
        self,
        store_manager: Optional[KnowledgeStoreManager] = None,
    ) -> None:
        self._engine = ProcessingEngine()
        self._engine.register_defaults()
        self._store_manager = store_manager or self._default_store_manager()
        self._processed_count = 0
        self._failed_count = 0
        self._reports: List[ProcessingReport] = []

    # ── Public API ──────────────────────────────

    def process(self, ingestion_doc: IngestionDocument) -> ProcessingReport:
        """Run the full intelligence pipeline on a single document.

        Returns a ``ProcessingReport`` with validation status, store
        identifiers, statistics, and timing information.
        """
        logger.info("Pipeline stage 1/2: processing {}", ingestion_doc.filename)
        start = time.time()

        # Stages 1-3: processor selection → native parsing → CDS
        doc = self._engine.process(ingestion_doc)

        # Stage 4: structural validation
        issues = validate_document(doc)
        validation_passed = len(issues) == 0

        # Stage 5-6: reference generation + relationship graph
        doc = _ensure_references(doc)
        doc = _build_relationship_graph(doc)

        computed = _compute_statistics(doc)
        doc.statistics = computed

        # Stage 7-8: serialization → knowledge store
        store_results: Dict[str, str] = {}
        if self._store_manager:
            source_id = ingestion_doc.checksum or ingestion_doc.id
            store_results = self._store_manager.store_across_all(doc, source_id)

        # Stage 9: report
        elapsed = time.time() - start
        report = ProcessingReport(
            source=ingestion_doc.filename,
            doc_type=doc.type,
            validation_passed=validation_passed,
            validation_issues=issues,
            store_results=store_results,
            processing_time_s=elapsed,
            statistics=doc.statistics,
        )
        self._reports.append(report)

        if validation_passed:
            self._processed_count += 1
            logger.info(
                "Pipeline: completed {} in {:.2f}s (validated, {} stores)",
                ingestion_doc.filename,
                elapsed,
                len(store_results),
            )
        else:
            self._failed_count += 1
            logger.warning(
                "Pipeline: completed {} with {} validation issues",
                ingestion_doc.filename,
                len(issues),
            )

        return report

    def process_many(self, docs: List[IngestionDocument]) -> List[ProcessingReport]:
        """Process multiple documents sequentially."""
        return [self.process(d) for d in docs]

    def summary(self) -> str:
        """Return a human-readable summary of all pipeline runs."""
        total = self._processed_count + self._failed_count
        lines = [
            "=" * 50,
            "  Document Intelligence Pipeline - Summary",
            "=" * 50,
            f"  Total processed: {total}",
            f"  Successful:      {self._processed_count}",
            f"  Failed:          {self._failed_count}",
        ]
        if self._processed_count > 0:
            avg_time = sum(r.processing_time_s for r in self._reports if r.validation_passed) / self._processed_count
            lines.append(f"  Avg time/doc:    {avg_time:.2f}s")
        lines.append("=" * 50)
        return "\n".join(lines)

    @property
    def reports(self) -> List[ProcessingReport]:
        return list(self._reports)

    @property
    def processed_count(self) -> int:
        return self._processed_count

    @property
    def failed_count(self) -> int:
        return self._failed_count

    # ── Internal ────────────────────────────────

    @staticmethod
    def _default_store_manager() -> KnowledgeStoreManager:
        mgr = KnowledgeStoreManager()
        mgr.register_defaults()
        return mgr


# ──────────────────────────────────────────────
#  Pipeline stage helpers
# ──────────────────────────────────────────────


# ── Helpers for accessing node fields (handle dataclass + dict) ──

def _n_id(node: Any) -> str:
    return node.id if hasattr(node, "id") else (node.get("id", "") if isinstance(node, dict) else "")


def _n_type(node: Any) -> str:
    return node.type if hasattr(node, "type") else (node.get("type", "") if isinstance(node, dict) else "")


def _n_content(node: Any) -> Any:
    return node.content if hasattr(node, "content") else (node.get("content") if isinstance(node, dict) else None)


def _n_reference(node: Any) -> Any:
    return node.reference if hasattr(node, "reference") else (node.get("reference") if isinstance(node, dict) else None)


def _n_parent_id(node: Any) -> Optional[str]:
    val = node.parent_id if hasattr(node, "parent_id") else (node.get("parent_id") if isinstance(node, dict) else None)
    return val


def _n_children(node: Any) -> List[Any]:
    if hasattr(node, "children"):
        return list(node.children)
    if isinstance(node, dict):
        return list(node.get("children", []))
    return []


def _ref_type(ref: Any) -> str:
    if ref is None:
        return ""
    if hasattr(ref, "type"):
        return ref.type or ""
    if isinstance(ref, dict):
        return ref.get("type", "")
    return ""


def _ref_location(ref: Any) -> Dict[str, Any]:
    if ref is None:
        return {}
    if hasattr(ref, "location"):
        return ref.location or {}
    if isinstance(ref, dict):
        return ref.get("location", {})
    return {}


def _ensure_references(doc: Document) -> Document:
    """Walk the ContentNode tree and ensure every node has a Reference.

    Nodes without a reference get an inferred one based on their
    parent's reference and node type.
    """
    if not doc.content_nodes:
        return doc

    default_ref = Reference(type=doc.type, location={"source": doc.source})

    def walk(nodes: List[Any], parent_ref: Optional[Any]) -> None:
        for node in nodes:
            if _n_reference(node) is None:
                ptype = _ref_type(parent_ref)
                ploc = _ref_location(parent_ref)
                inferred = Reference(
                    type=ptype or doc.type,
                    location={**ploc, "auto_generated": True},
                )
                if hasattr(node, "reference"):
                    node.reference = inferred
                elif isinstance(node, dict):
                    node["reference"] = {"type": inferred.type, "location": inferred.location}
            walk(_n_children(node), _n_reference(node))

    walk(doc.content_nodes, default_ref)
    return doc


def _build_relationship_graph(doc: Document) -> Document:
    """Build a complete RelationshipGraph from the ContentNode hierarchy.

    Creates ``child_of`` edges for every parent-child relationship.
    Existing edges in the graph are preserved.
    """
    all_nodes: Dict[str, Any] = {}
    edges: List[Edge] = []
    seen_edge_pairs: set = set()

    def walk(nodes: List[Any]) -> None:
        for node in nodes:
            nid = _n_id(node)
            if nid:
                all_nodes[nid] = node
            pid = _n_parent_id(node)
            if nid and pid:
                pair = (nid, pid, "child_of")
                if pair not in seen_edge_pairs:
                    seen_edge_pairs.add(pair)
                    edges.append(
                        Edge(source=nid, target=pid, relationship_type="child_of", confidence=1.0)
                    )
            walk(_n_children(node))

    walk(doc.content_nodes)

    # Preserve any existing edges from the graph
    rg = doc.relationship_graph
    existing_edges = rg.edges if hasattr(rg, "edges") else (rg.get("edges", []) if isinstance(rg, dict) else [])
    for ee in existing_edges:
        src = ee.source if hasattr(ee, "source") else (ee.get("source", "") if isinstance(ee, dict) else "")
        tgt = ee.target if hasattr(ee, "target") else (ee.get("target", "") if isinstance(ee, dict) else "")
        rtype = (
            ee.relationship_type
            if hasattr(ee, "relationship_type")
            else (ee.get("relationship_type", "") if isinstance(ee, dict) else "")
        )
        pair = (src, tgt, rtype)
        if pair not in seen_edge_pairs:
            seen_edge_pairs.add(pair)
            edges.append(ee)

    doc.relationship_graph = RelationshipGraph(nodes=all_nodes, edges=edges)
    return doc


def _compute_statistics(doc: Document) -> Statistics:
    """Compute aggregate statistics from the ContentNode hierarchy."""
    type_counts: Dict[str, int] = {}
    total = 0
    max_depth = 0

    def walk(nodes: List[Any], depth: int = 0) -> None:
        nonlocal total, max_depth
        for node in nodes:
            total += 1
            max_depth = max(max_depth, depth)
            ntype = _n_type(node) or "unknown"
            type_counts[ntype] = type_counts.get(ntype, 0) + 1
            walk(_n_children(node), depth + 1)

    walk(doc.content_nodes)

    edge_count = 0
    rg = doc.relationship_graph
    if hasattr(rg, "edges") and isinstance(rg.edges, list):
        edge_count = len(rg.edges)
    elif isinstance(rg, dict):
        edge_count = len(rg.get("edges", []))

    return Statistics(
        total_content_nodes=total,
        total_relationships=edge_count,
        node_type_counts=type_counts,
        max_depth=max_depth,
    )
