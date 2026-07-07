"""Confidence calculation — computes final confidence scores based on validation results.

Profiling instrumentation added.
"""

import time
from typing import Any, Iterable, List

from backend.logger import logger
from validation.confidence_breakdown import ConfidenceBreakdown
from validation.config import ValidationConfig
from validation.models.validation_report import ValidationReport


class ConfidenceEngineResults:
    """Results of confidence calculation."""
    
    def __init__(self, confidence_breakdown, overall_score, confidence_level, validation_status, has_hallucinations):
        self.confidence_breakdown = confidence_breakdown
        self.overall_score = overall_score
        self.confidence_level = confidence_level
        self.validation_status = validation_status
        self.has_hallucinations = has_hallucinations


class ConfidenceEngine:
    """Computes confidence scores for the validation pipeline."""

    def __init__(self, config: Any = None) -> None:
        self.config = config or ValidationConfig()

    def compute(
        self,
        evidence_results: Any,
        citation_results: Any,
        entity_results: Any,
        relationship_results: Any,
        consistency_results: Any,
        hallucination_results: Any,
        safety_results: Any,
        context_package: Any,
    ) -> Any:
        """Compute confidence scores based on validation results.

        Parameters
        ----------
        evidence_results : Any
            Evidence validation results.
        citation_results : Any
            Citation validation results.
        entity_results : Any
            Entity validation results.
        relationship_results : Any
            Relationship validation results.
        consistency_results : Any
            Consistency check results.
        hallucination_results : Any
            Hallucination detection results.
        safety_results : Any
            Safety validation results.
        context_package : Any
            The Structured Context Package.

        Returns
        -------
        ConfidenceEngineResults
            Computed confidence scores and validation status.
        """
        start = time.time()
        logger.info("ConfidenceEngine: starting confidence calculation")

        # Simulate confidence calculation based on validation results
        confidence_results = self._compute_confidence(
            evidence_results, citation_results, entity_results,
            relationship_results, consistency_results,
            hallucination_results, safety_results, context_package
        )
        elapsed_ms = (time.time() - start) * 1000
        logger.info("ConfidenceEngine: completed in %.3f ms",
                     elapsed_ms)

        return confidence_results

    def _compute_confidence(
        self,
        evidence_results: Any,
        citation_results: Any,
        entity_results: Any,
        relationship_results: Any,
        consistency_results: Any,
        hallucination_results: Any,
        safety_results: Any,
        context_package: Any,
    ) -> Any:
        """Internal confidence calculation logic."""

        evidence_valid = self._items(evidence_results, "validated_claims")
        evidence_failed = self._items(evidence_results, "failed_claims")
        evidence_unsupported = self._items(evidence_results, "unsupported_claims")
        evidence_total = len(evidence_valid) + len(evidence_failed) + len(evidence_unsupported)
        evidence_score = self._ratio(len(evidence_valid), evidence_total, default=0.0)

        valid_citations = self._items(citation_results, "valid_citations")
        invalid_citations = self._items(citation_results, "invalid_citations")
        citation_total = len(valid_citations) + len(invalid_citations)
        citation_score = self._ratio(
            len(valid_citations),
            citation_total,
            default=0.0 if self._get_config("mandatory_citations", True) else 1.0,
        )

        validated_entities = self._items(entity_results, "validated_entities")
        missing_entities = self._items(entity_results, "missing_entities")
        entity_total = len(validated_entities) + len(missing_entities)
        entity_score = self._ratio(len(validated_entities), entity_total, default=1.0)

        valid_relationships = self._items(relationship_results, "validated_relationships")
        failed_relationships = self._items(relationship_results, "failed_relationships")
        relationship_total = len(valid_relationships) + len(failed_relationships)
        relationship_score = self._ratio(len(valid_relationships), relationship_total, default=1.0)

        consistency_score = self._consistency_score(consistency_results)
        retrieval_score = self._retrieval_score(context_package)

        has_hallucinations = bool(self._field(hallucination_results, "has_hallucinations", False))
        hallucination_score = 0.0 if has_hallucinations else 1.0

        weights = {
            "evidence": self._get_config("weight_evidence_coverage", 0.25),
            "citation": self._get_config("weight_citation_validity", 0.15),
            "retrieval": self._get_config("weight_retrieval_score", 0.15),
            "entity": self._get_config("weight_entity_validation", 0.15),
            "relationship": self._get_config("weight_relationship_validation", 0.10),
            "consistency": self._get_config("weight_consistency", 0.10),
            "hallucination": self._get_config("weight_hallucination_detection", 0.10),
        }

        overall_score = (
            evidence_score * weights["evidence"] +
            citation_score * weights["citation"] +
            retrieval_score * weights["retrieval"] +
            entity_score * weights["entity"] +
            relationship_score * weights["relationship"] +
            consistency_score * weights["consistency"] +
            hallucination_score * weights["hallucination"]
        ) / max(sum(weights.values()), 1e-9)

        # Determine confidence level
        if overall_score >= 0.9:
            level = "HIGH"
        elif overall_score >= 0.8:
            level = "MEDIUM"
        elif overall_score >= 0.7:
            level = "LOW"
        else:
            level = "UNKNOWN"

        if self._field(safety_results, "is_safe", True) is False:
            validation_status = "FAILED_SAFETY"
        elif has_hallucinations:
            validation_status = "FAILED_HALLUCINATION"
        elif self._get_config("mandatory_citations", True) and citation_score < 1.0:
            validation_status = "FAILED_CITATION"
        elif evidence_total > 0 and evidence_score < self._get_config("required_evidence_coverage", 0.9):
            validation_status = "FAILED_EVIDENCE"
        elif overall_score < self._get_config("confidence_threshold", 0.85):
            validation_status = "FAILED"
        else:
            validation_status = "PASSED"

        # Create confidence breakdown
        confidence_breakdown = ConfidenceBreakdown(
            evidence_coverage=evidence_score,
            citation_validity=citation_score,
            retrieval_score=retrieval_score,
            entity_validation=entity_score,
            relationship_validation=relationship_score,
            consistency=consistency_score,
            hallucination_detection=hallucination_score
        )

        # Create results object
        class SimpleConfidenceResults:
            def __init__(self):
                self.confidence_breakdown = confidence_breakdown
                self.overall_score = overall_score
                self.confidence_level = level
                self.validation_status = validation_status
                self.has_hallucinations = has_hallucinations

        return SimpleConfidenceResults()

    @staticmethod
    def _field(item: Any, name: str, default: Any = None) -> Any:
        if isinstance(item, dict):
            return item.get(name, default)
        return getattr(item, name, default)

    def _items(self, item: Any, name: str) -> List[Any]:
        value = self._field(item, name, [])
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, tuple):
            return list(value)
        if isinstance(value, Iterable) and not isinstance(value, (str, bytes, dict)):
            return list(value)
        return []

    @staticmethod
    def _ratio(numerator: int, denominator: int, default: float) -> float:
        if denominator <= 0:
            return default
        return max(0.0, min(1.0, numerator / denominator))

    def _get_config(self, name: str, default: Any) -> Any:
        if isinstance(self.config, dict):
            return self.config.get(name, default)
        return getattr(self.config, name, default)

    def _consistency_score(self, consistency_results: Any) -> float:
        if consistency_results is None:
            return 0.0
        if self._field(consistency_results, "is_consistent", False):
            return 1.0
        issues = len(self._items(consistency_results, "issues"))
        penalty = self._get_config("consistency_issue_penalty", 0.1)
        return max(0.0, 1.0 - issues * penalty)

    def _retrieval_score(self, context_package: Any) -> float:
        if context_package is None:
            return 0.0
        package_confidence = self._field(context_package, "confidence", None)
        if isinstance(package_confidence, (int, float)) and package_confidence > 0:
            return max(0.0, min(1.0, float(package_confidence)))
        total_results = self._field(context_package, "total_results", 0) or 0
        if total_results <= 0 and hasattr(context_package, "all_results"):
            total_results = len(context_package.all_results)
        return max(0.0, min(1.0, total_results / 5.0))
