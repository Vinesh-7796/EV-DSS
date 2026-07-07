"""Data models for the retrieval infrastructure.

Defines the input/output contracts for every stage in the retrieval
pipeline and the final ``StructuredContextPackage`` delivered to the
downstream diagnostic assistant.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class RetrievalMethod(str, Enum):
    """Identifies which retrieval strategy produced a result."""

    VECTOR = "vector"
    SQL_EXACT = "sql_exact"
    GRAPH = "graph"
    IMAGE = "image"


@dataclass
class RetrievedChunk:
    """A chunk of text that was retrieved as semantically relevant."""

    chunk_id: str = ""
    text: str = ""
    node_type: str = ""
    source: str = ""
    document_id: str = ""
    section_title: str = ""
    page_number: int = 0
    score: float = 0.0
    method: RetrievalMethod = RetrievalMethod.VECTOR
    metadata: Dict[str, Any] = field(default_factory=dict)
    reference: Optional[Dict[str, Any]] = None


@dataclass
class RetrievalResult:
    """A single result item in the structured context package.

    Carries the retrieved content, provenance, confidence score, and
    the method that produced it.
    """

    content: str = ""
    node_id: str = ""
    node_type: str = ""
    source: str = ""
    document_id: str = ""
    score: float = 0.0
    rank: int = 0
    method: RetrievalMethod = RetrievalMethod.VECTOR
    metadata: Dict[str, Any] = field(default_factory=dict)
    reference: Optional[Dict[str, Any]] = None

    def to_citation(self) -> str:
        """Format as a citation string for the context package."""
        src = self.source or "unknown"
        ref = self.reference or {}
        loc = ref.get("location", {})
        parts = [src]
        if loc.get("page"):
            parts.append(f"p.{loc['page']}")
        if loc.get("section"):
            parts.append(f"§{loc['section']}")
        return f"{' | '.join(parts)}  ({self.method.value}, score={self.score:.3f})"


@dataclass
class RetrievalQuery:
    """Normalised query object passed through the retrieval engine."""

    raw_text: str = ""
    embedding: Optional[List[float]] = None
    top_k_vector: int = 10
    top_k_graph: int = 10
    top_k_sql: int = 10
    top_k_image: int = 5
    filters: Dict[str, Any] = field(default_factory=dict)
    entity_ids: Optional[List[str]] = None
    document_ids: Optional[List[str]] = None


@dataclass
class StructuredContextPackage:
    """The final output of the hybrid retrieval engine.

    This is a fully grounded context package ready for an LLM, containing
    all semantic context, exact matches, graph context, image references,
    citations, and confidence metadata — no additional searching required.
    """

    query: str = ""
    semantic_context: List[RetrievalResult] = field(default_factory=list)
    exact_matches: List[RetrievalResult] = field(default_factory=list)
    graph_context: List[RetrievalResult] = field(default_factory=list)
    image_references: List[RetrievalResult] = field(default_factory=list)
    citations: List[str] = field(default_factory=list)
    confidence: float = 0.0
    processing_time_ms: float = 0.0
    total_results: int = 0
    deduplicated_count: int = 0
    methods_used: List[str] = field(default_factory=list)

    def merge(self, other: "StructuredContextPackage") -> "StructuredContextPackage":
        """Merge another context package into this one (for multi-step queries)."""
        self.semantic_context.extend(other.semantic_context)
        self.exact_matches.extend(other.exact_matches)
        self.graph_context.extend(other.graph_context)
        self.image_references.extend(other.image_references)
        self.citations.extend(other.citations)
        self.total_results += other.total_results
        self.deduplicated_count += other.deduplicated_count
        self.processing_time_ms += other.processing_time_ms
        for m in other.methods_used:
            if m not in self.methods_used:
                self.methods_used.append(m)
        return self

    @property
    def all_results(self) -> List[RetrievalResult]:
        """Flatten all result categories into a single ranked list."""
        results = []
        results.extend(self.semantic_context)
        results.extend(self.exact_matches)
        results.extend(self.graph_context)
        results.extend(self.image_references)
        results.sort(key=lambda r: r.score, reverse=True)
        for i, r in enumerate(results, 1):
            r.rank = i
        return results
