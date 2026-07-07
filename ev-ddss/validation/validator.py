"""Retrieval Validator — runs evaluation queries through the retrieval
engine and aggregates metrics.

Supports batch evaluation from a query relevance dataset and produces
a summary report.
"""

import time
from dataclasses import dataclass, field
from statistics import mean
from typing import Any, Dict, List, Optional, Set

from backend.logger import logger
from retrieval.engine import HybridRetrievalEngine
from retrieval.models import StructuredContextPackage
from validation.metrics import RetrievalMetrics, evaluate_retrieval


@dataclass
class ValidationResult:
    """Aggregated results of a validation run."""

    total_queries: int = 0
    metrics: List[RetrievalMetrics] = field(default_factory=list)
    avg_precision_at_k: Dict[int, float] = field(default_factory=dict)
    avg_recall_at_k: Dict[int, float] = field(default_factory=dict)
    avg_mrr: float = 0.0
    avg_latency_ms: float = 0.0
    avg_duplicate_rate: float = 0.0
    avg_context_completeness: float = 0.0
    avg_confidence: float = 0.0
    failed_queries: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_queries": self.total_queries,
            "avg_precision_at_k": self.avg_precision_at_k,
            "avg_recall_at_k": self.avg_recall_at_k,
            "avg_mrr": self.avg_mrr,
            "avg_latency_ms": self.avg_latency_ms,
            "avg_duplicate_rate": self.avg_duplicate_rate,
            "avg_context_completeness": self.avg_context_completeness,
            "avg_confidence": self.avg_confidence,
            "failed_queries": self.failed_queries,
        }

    def summary(self) -> str:
        lines = [
            "=" * 55,
            "  Retrieval Validation Summary",
            "=" * 55,
            f"  Queries:            {self.total_queries} ({self.failed_queries} failed)",
            f"  MRR:                {self.avg_mrr:.4f}",
            f"  Latency (avg):      {self.avg_latency_ms:.1f}ms",
            f"  Duplicate rate:     {self.avg_duplicate_rate:.3f}",
            f"  Context completeness: {self.avg_context_completeness:.3f}",
            f"  Confidence (avg):   {self.avg_confidence:.3f}",
        ]
        for k in sorted(self.avg_precision_at_k):
            lines.append(f"  Precision@{k:<3d}:        {self.avg_precision_at_k[k]:.4f}")
        for k in sorted(self.avg_recall_at_k):
            lines.append(f"  Recall@{k:<3d}:           {self.avg_recall_at_k[k]:.4f}")
        lines.append("=" * 55)
        return "\n".join(lines)


class RetrievalValidator:
    """Evaluates the hybrid retrieval engine against a set of test queries.

    Usage::

        validator = RetrievalValidator(engine)
        result = validator.run(test_queries)
        print(result.summary())
    """

    def __init__(self, engine: HybridRetrievalEngine) -> None:
        self._engine = engine

    def run(
        self,
        test_queries: List[Dict[str, Any]],
    ) -> ValidationResult:
        """Run validation against a list of test queries.

        Each test query is a dict with::

            {"query": str, "relevant_ids": List[str]}

        Parameters
        ----------
        test_queries : list of dict
            Test queries with ground-truth relevant document IDs.

        Returns
        -------
        ValidationResult
            Aggregated metrics.
        """
        if not self._engine.is_initialized:
            self._engine.initialize()

        result = ValidationResult(total_queries=len(test_queries))

        for tq in test_queries:
            query = tq.get("query", "")
            relevant_ids = set(tq.get("relevant_ids", []))

            if not query:
                continue

            try:
                package = self._engine.retrieve(query)
            except Exception as exc:
                logger.warning("Validation: query '{}' failed: {}", query[:80], exc)
                result.failed_queries += 1
                continue

            metrics = evaluate_retrieval(
                query=query,
                package=package,
                relevant_node_ids=relevant_ids if relevant_ids else None,
            )
            result.metrics.append(metrics)

        # Compute averages
        if result.metrics:
            m = result.metrics
            result.avg_mrr = mean(getattr(mm, "mean_reciprocal_rank", 0.0) for mm in m)
            result.avg_latency_ms = mean(getattr(mm, "latency_ms", 0.0) for mm in m)
            result.avg_duplicate_rate = mean(getattr(mm, "duplicate_rate", 0.0) for mm in m)
            result.avg_context_completeness = mean(getattr(mm, "context_completeness", 0.0) for mm in m)
            result.avg_confidence = mean(getattr(mm, "confidence", 0.0) for mm in m)

            # Precision / Recall per k
            all_pk: Dict[int, List[float]] = {}
            all_rk: Dict[int, List[float]] = {}
            for mm in m:
                for k, v in mm.precision_at_k.items():
                    all_pk.setdefault(k, []).append(v)
                for k, v in mm.recall_at_k.items():
                    all_rk.setdefault(k, []).append(v)
            for k in sorted(all_pk):
                result.avg_precision_at_k[k] = mean(all_pk[k])
            for k in sorted(all_rk):
                result.avg_recall_at_k[k] = mean(all_rk[k])

        return result
