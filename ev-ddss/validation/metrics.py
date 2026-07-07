"""Retrieval Evaluation Metrics — quantitative assessment of retrieval
quality.

Metrics
───────

* **Retrieval Accuracy** — How many relevant results appear in top-k.
* **Duplicate Context Rate** — Fraction of results that are near-duplicates.
* **Ranking Quality (MRR / NDCG)** — How well relevant results are ranked.
* **Response Latency** — End-to-end retrieval time.
* **Context Completeness** — Coverage of expected information categories.
* **Precision / Recall @ k** — Standard IR metrics.
"""

import time
from dataclasses import dataclass, field
from statistics import mean
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from retrieval.models import RetrievalResult, StructuredContextPackage


@dataclass
class RetrievalMetrics:
    """Container for all retrieval quality metrics for a single query."""

    query: str = ""
    precision_at_k: Dict[int, float] = field(default_factory=dict)
    recall_at_k: Dict[int, float] = field(default_factory=dict)
    mean_reciprocal_rank: float = 0.0
    ndcg_at_k: Dict[int, float] = field(default_factory=dict)
    duplicate_rate: float = 0.0
    latency_ms: float = 0.0
    context_completeness: float = 0.0
    total_results: int = 0
    method_coverage: List[str] = field(default_factory=list)
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "precision_at_k": self.precision_at_k,
            "recall_at_k": self.recall_at_k,
            "mean_reciprocal_rank": self.mean_reciprocal_rank,
            "ndcg_at_k": self.ndcg_at_k,
            "duplicate_rate": self.duplicate_rate,
            "latency_ms": self.latency_ms,
            "context_completeness": self.context_completeness,
            "total_results": self.total_results,
            "method_coverage": self.method_coverage,
            "confidence": self.confidence,
        }


def _precision_at_k(
    retrieved: List[RetrievalResult],
    relevant_ids: Set[str],
    k: int,
) -> float:
    """Precision @ k = |relevant ∩ top-k| / k."""
    if k <= 0:
        return 0.0
    top_k = retrieved[:k]
    relevant_count = sum(1 for r in top_k if r.node_id in relevant_ids)
    return relevant_count / k


def _recall_at_k(
    retrieved: List[RetrievalResult],
    relevant_ids: Set[str],
    k: int,
    total_relevant: int,
) -> float:
    """Recall @ k = |relevant ∩ top-k| / total_relevant."""
    if total_relevant <= 0:
        return 0.0
    top_k = retrieved[:k]
    relevant_count = sum(1 for r in top_k if r.node_id in relevant_ids)
    return relevant_count / total_relevant


def _reciprocal_rank(
    retrieved: List[RetrievalResult],
    relevant_ids: Set[str],
) -> float:
    """Reciprocal rank of the first relevant result."""
    for i, r in enumerate(retrieved, 1):
        if r.node_id in relevant_ids:
            return 1.0 / i
    return 0.0


def _dcg(relevances: List[float], k: int) -> float:
    """Discounted cumulative gain at k."""
    import math
    dcg = 0.0
    for i in range(min(k, len(relevances))):
        dcg += (2 ** relevances[i] - 1) / math.log2(i + 2)
    return dcg


def _ndcg_at_k(
    retrieved: List[RetrievalResult],
    relevance_fn: Callable[[RetrievalResult], float],
    k: int,
) -> float:
    """Normalised DCG at k."""
    relevances = [relevance_fn(r) for r in retrieved[:k]]
    ideal = sorted(relevances, reverse=True)
    dcg = _dcg(relevances, k)
    idcg = _dcg(ideal, k)
    return dcg / idcg if idcg > 0 else 0.0


def _detect_duplicates(results: List[RetrievalResult]) -> int:
    """Count near-duplicate results by content similarity."""
    seen: Set[str] = set()
    duplicates = 0
    for r in results:
        content_key = r.content[:150].strip().lower()
        if content_key in seen:
            duplicates += 1
        else:
            seen.add(content_key)
    return duplicates


def evaluate_retrieval(
    query: str,
    package: StructuredContextPackage,
    relevant_node_ids: Optional[Set[str]] = None,
    relevance_fn: Optional[Callable[[RetrievalResult], float]] = None,
    total_relevant: Optional[int] = None,
) -> RetrievalMetrics:
    """Compute retrieval metrics for a single query.

    Parameters
    ----------
    query : str
        The original query.
    package : StructuredContextPackage
        The retrieval output.
    relevant_node_ids : Set[str] or None
        Ground-truth relevant node IDs. If None, only structural metrics
        are computed (no precision/recall).
    relevance_fn : callable or None
        Function that maps a RetrievalResult to a relevance grade (0.0–1.0).
        Used for NDCG. Defaults to using the result's own score.
    total_relevant : int or None
        Total number of relevant documents. If None, approximated from
        ``relevant_node_ids``.

    Returns
    -------
    RetrievalMetrics
    """
    if relevance_fn is None:
        relevance_fn = lambda r: r.score  # noqa: E731

    all_results = package.all_results
    metrics = RetrievalMetrics(
        query=query,
        latency_ms=package.processing_time_ms,
        total_results=len(all_results),
        method_coverage=package.methods_used,
        confidence=package.confidence,
    )

    # Precision / Recall @ k
    if relevant_node_ids is not None:
        n_relevant = total_relevant or len(relevant_node_ids)
        for k in [1, 3, 5, 10, 20]:
            if k <= len(all_results):
                metrics.precision_at_k[k] = _precision_at_k(all_results, relevant_node_ids, k)
                metrics.recall_at_k[k] = _recall_at_k(all_results, relevant_node_ids, k, n_relevant)

        metrics.mean_reciprocal_rank = _reciprocal_rank(all_results, relevant_node_ids)

    # NDCG @ k
    for k in [5, 10, 20]:
        if k <= len(all_results):
            metrics.ndcg_at_k[k] = _ndcg_at_k(all_results, relevance_fn, k)

    # Duplicate rate
    dup_count = _detect_duplicates(all_results)
    metrics.duplicate_rate = dup_count / max(len(all_results), 1)

    # Context completeness — based on method coverage
    method_names = set(package.methods_used)
    expected = {"vector", "sql_exact", "graph", "image"}
    metrics.context_completeness = len(method_names & expected) / len(expected)

    return metrics
