"""Context Optimizer — prepares a StructuredContextPackage for the LLM.

Responsibilities
────────────────

* Remove duplicate evidence (by node_id or content fingerprint).
* Remove redundant citations.
* Rank results by retrieval score.
* Respect a configurable token budget using model-aware token estimation.
* Never modify factual information or generate new content.
"""

from typing import Any, Dict, List, Set

from backend.logger import logger
from reasoning.token_estimator import TokenEstimator
from retrieval.models import RetrievalResult, StructuredContextPackage


def _content_fingerprint(text: str) -> str:
    """Normalised fingerprint for near-duplicate detection."""
    return text.strip().lower()[:200]


class ContextOptimizer:
    """Optimises a ``StructuredContextPackage`` for LLM ingestion.

    Parameters
    ----------
    max_tokens : int
        Maximum total tokens across all context sections.
    deduplicate : bool
        Whether to remove duplicate / near-duplicate entries.
    rank_by_score : bool
        Whether to sort results by retrieval score (highest first).
    token_estimator : TokenEstimator or None
        Token estimator instance. Creates a default one if not provided.
    """

    def __init__(
        self,
        max_tokens: int = 4096,
        deduplicate: bool = True,
        rank_by_score: bool = True,
        token_estimator: Optional[TokenEstimator] = None,
    ) -> None:
        self._max_tokens = max_tokens
        self._deduplicate = deduplicate
        self._rank_by_score = rank_by_score
        self._token_estimator = token_estimator or TokenEstimator()

    # ── Public API ──────────────────────────────

    def optimize(self, package: StructuredContextPackage) -> StructuredContextPackage:
        """Return a new ``StructuredContextPackage`` with optimised context.

        The original package is never mutated.
        """
        if not package:
            return package

        optimized = StructuredContextPackage(
            query=package.query,
            citations=list(package.citations),
            confidence=package.confidence,
            processing_time_ms=package.processing_time_ms,
            methods_used=list(package.methods_used),
        )

        optimized.semantic_context = self._optimize_results(package.semantic_context)
        optimized.exact_matches = self._optimize_results(package.exact_matches)
        optimized.graph_context = self._optimize_results(package.graph_context)
        optimized.image_references = self._optimize_results(package.image_references)

        budget = self._max_tokens
        for attr_name, results in [
            ("semantic_context", optimized.semantic_context),
            ("exact_matches", optimized.exact_matches),
            ("graph_context", optimized.graph_context),
            ("image_references", optimized.image_references),
        ]:
            kept: List[RetrievalResult] = []
            for r in results:
                tokens = self._token_estimator.estimate(r.content)
                if tokens <= budget:
                    kept.append(r)
                    budget -= tokens
                else:
                    break
            setattr(optimized, attr_name, kept)

        optimized.total_results = (
            len(optimized.semantic_context)
            + len(optimized.exact_matches)
            + len(optimized.graph_context)
            + len(optimized.image_references)
        )

        logger.debug(
            "ContextOptimizer: {} → {} results, {}/{} tokens (estimator={})",
            package.total_results,
            optimized.total_results,
            self._max_tokens - budget,
            self._max_tokens,
            self._token_estimator.model_name or "fallback",
        )
        return optimized

    # ── Internal ────────────────────────────────

    def _optimize_results(self, results: List[RetrievalResult]) -> List[RetrievalResult]:
        if not results:
            return []
        items = list(results)

        if self._deduplicate:
            items = self._deduplicate_results(items)

        if self._rank_by_score:
            items.sort(key=lambda r: r.score, reverse=True)

        for i, r in enumerate(items, 1):
            r.rank = i

        return items

    @staticmethod
    def _deduplicate_results(results: List[RetrievalResult]) -> List[RetrievalResult]:
        seen_ids: Set[str] = set()
        seen_fingerprints: Set[str] = set()
        deduped: List[RetrievalResult] = []

        for r in results:
            if r.node_id and r.node_id in seen_ids:
                continue
            if r.node_id:
                seen_ids.add(r.node_id)

            fp = _content_fingerprint(r.content)
            if fp in seen_fingerprints:
                continue
            seen_fingerprints.add(fp)

            deduped.append(r)

        return deduped
