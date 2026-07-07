"""Evidence validation — matches LLM claims against retrieved context.

Profiling instrumentation added.
"""

import time
from typing import Any, List
from dataclasses import dataclass, field

from backend.logger import logger


@dataclass
class EvidenceValidationResults:
    validated_claims: List[Any] = field(default_factory=list)
    failed_claims: List[Any] = field(default_factory=list)
    unsupported_claims: List[Any] = field(default_factory=list)


@dataclass
class ClaimValidationResult:
    claim: str
    is_supported: bool
    validator: str
    validation_status: str
    evidence_ids: List[str]
    reason: str
    errors: List[str] = None


class EvidenceValidator:
    """Validates that every claim in the diagnostic response is supported by the retrieved context."""

    def __init__(self) -> None:
        pass

    def validate(self, diagnostic_response: Any, context_package: Any) -> Any:
        """Validate evidence claims against retrieved context.

        Parameters
        ----------
        diagnostic_response : Any
            The LLM-generated diagnostic response to validate.
        context_package : Any
            The Structured Context Package containing retrieved context.

        Returns
        -------
        Any
            Validation results containing validated claims, failed claims, and unsupported claims.
        """
        start = time.time()
        logger.info("EvidenceValidator: starting validation")

        # Simulate evidence validation with profiling
        validation_results = self._validate_claims(diagnostic_response, context_package)
        elapsed_ms = (time.time() - start) * 1000
        logger.info("EvidenceValidator: completed in %.3f ms, %d validated claims",
                     elapsed_ms, len(validation_results.validated_claims))

        return validation_results

    def _validate_claims(self, diagnostic_response: Any, context_package: Any) -> Any:
        """Internal claim validation logic."""

        validated_claims = []
        failed_claims = []
        unsupported_claims = []

        # Simulate parsing claims from diagnostic response
        claims = self._extract_claims(diagnostic_response)

        # If there are no claims, create a dummy result
        if not claims:
            # Create a minimal valid result structure
            class SimpleEvidenceResults:
                def __init__(self):
                    self.validated_claims = []
                    self.failed_claims = []
                    self.unsupported_claims = []
            return SimpleEvidenceResults()

        # Simulate claim validation with actual data
        for i, claim in enumerate(claims):
            # Check if claim is supported by context
            is_supported = self._is_claim_supported(claim, context_package)

            validator = ClaimValidationResult(
                claim=claim,
                is_supported=is_supported,
                validator="EvidenceValidator",
                validation_status="PASS" if is_supported else "FAIL",
                evidence_ids=self._find_evidence_ids(claim, context_package),
                reason=f"Claim validated against retrieved context (simulated support: {is_supported})",
            )

            if is_supported:
                validated_claims.append(validator)
            else:
                failed_claims.append(validator)

        class MinimalEvidenceResults:
            def __init__(self):
                self.validated_claims = validated_claims
                self.failed_claims = failed_claims
                self.unsupported_claims = unsupported_claims

        return MinimalEvidenceResults()

    def _extract_claims(self, diagnostic_response: Any) -> List[str]:
        """Extract concise claims from a diagnostic response object or dict."""
        claims: List[str] = []

        def add(value: Any) -> None:
            if isinstance(value, str) and value.strip():
                claims.append(value.strip())
            elif isinstance(value, list):
                for item in value:
                    add(item)

        if hasattr(diagnostic_response, "problem_summary"):
            add(getattr(diagnostic_response, "problem_summary", ""))
            add(getattr(diagnostic_response, "possible_causes", []))
            add(getattr(diagnostic_response, "recommended_actions", []))
        elif isinstance(diagnostic_response, dict):
            add(diagnostic_response.get("problem_summary", ""))
            add(diagnostic_response.get("possible_causes", []))
            add(diagnostic_response.get("recommended_actions", []))

        return claims

    def _is_claim_supported(self, claim: str, context_package: Any) -> bool:
        context_text = " ".join(self._context_texts(context_package)).lower()
        if not context_text:
            return False
        claim_terms = {
            term.strip(".,:;()[]{}").lower()
            for term in claim.split()
            if len(term.strip(".,:;()[]{}")) >= 4
        }
        if not claim_terms:
            return False
        matches = sum(1 for term in claim_terms if term in context_text)
        return matches > 0

    def _find_evidence_ids(self, claim: str, context_package: Any) -> List[str]:
        claim_lower = claim.lower()
        evidence_ids: List[str] = []
        for result in self._context_results(context_package):
            content = getattr(result, "content", "").lower()
            node_id = getattr(result, "node_id", "")
            if node_id and any(term in content for term in claim_lower.split() if len(term) >= 4):
                evidence_ids.append(node_id)
        return evidence_ids[:5]

    def _context_texts(self, context_package: Any) -> List[str]:
        return [getattr(result, "content", "") for result in self._context_results(context_package)]

    def _context_results(self, context_package: Any) -> List[Any]:
        if not context_package:
            return []
        if hasattr(context_package, "all_results"):
            return list(context_package.all_results)
        results: List[Any] = []
        for attr in ("semantic_context", "exact_matches", "graph_context", "image_references"):
            results.extend(getattr(context_package, attr, []) or [])
        return results
