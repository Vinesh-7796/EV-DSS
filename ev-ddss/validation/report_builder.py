from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field

from validation.models.diagnostic_response import DiagnosticResponse
from validation.models.validation_report import (
    ValidationReport,
    ClaimValidationResult,
    CitationValidationResult,
    EntityValidationResult,
    RelationshipValidationResult,
    HallucinationResult,
    ConfidenceBreakdown,
)
from validation.evidence_validator import EvidenceValidationResults
from validation.citation_validator import CitationValidationResults
from validation.entity_validator import EntityValidationResults
from validation.relationship_validator import RelationshipValidationResults
from validation.consistency_checker import ConsistencyValidationResults
from validation.hallucination_detector import HallucinationDetectionResults
from validation.safety_validator import SafetyValidationResults
from validation.confidence_engine import ConfidenceEngineResults, ConfidenceEngine
from validation.config import ValidationConfig

@dataclass
class BuildingResults:
    """Results of report building."""
    validation_report: ValidationReport = field(default_factory=ValidationReport)
    validated_response: Any = None  # ValidatedDiagnosticResponse
    metadata: Dict[str, Any] = field(default_factory=dict)

class ReportBuilder:
    """Builds comprehensive validation reports and validated responses."""

    def __init__(self, config: ValidationConfig):
        """
        Parameters
        ----------
        config : ValidationConfig
            Configuration for validation.
        """
        self.config = config

    def build_report(
        self,
        diagnostic_response: DiagnosticResponse,
        evidence_results: EvidenceValidationResults,
        citation_results: CitationValidationResults,
        entity_results: EntityValidationResults,
        relationship_results: RelationshipValidationResults,
        consistency_results: ConsistencyValidationResults,
        hallucination_results: HallucinationDetectionResults,
        safety_results: SafetyValidationResults,
        confidence_results: ConfidenceEngineResults,
    ) -> BuildingResults:
        """Build a comprehensive validation report and validated response."""
        validation_report = self._build_validation_report(
            diagnostic_response,
            evidence_results,
            citation_results,
            entity_results,
            relationship_results,
            consistency_results,
            hallucination_results,
            safety_results,
            confidence_results,
        )

        validated_response = self._build_validated_response(
            diagnostic_response,
            validation_report,
            evidence_results,
            citation_results,
            entity_results,
            relationship_results,
            safety_results,
            confidence_results,
        )

        metadata = self._build_metadata(
            diagnostic_response,
            validation_report,
            confidence_results,
        )

        return BuildingResults(
            validation_report=validation_report,
            validated_response=validated_response,
            metadata=metadata,
        )

    def _build_validation_report(
        self,
        diagnostic_response: DiagnosticResponse,
        evidence_results: EvidenceValidationResults,
        citation_results: CitationValidationResults,
        entity_results: EntityValidationResults,
        relationship_results: RelationshipValidationResults,
        consistency_results: ConsistencyValidationResults,
        hallucination_results: HallucinationDetectionResults,
        safety_results: SafetyValidationResults,
        confidence_results: ConfidenceEngineResults,
    ) -> ValidationReport:
        """Build a comprehensive validation report with full traceability."""

        # Convert evidence results — preserve validator and evidence_ids
        validated_claims = []
        for claim_result in evidence_results.validated_claims:
            validated_claims.append(
                ClaimValidationResult(
                    claim=claim_result.claim,
                    is_supported=True,
                    validator=claim_result.validator,
                    validation_status=claim_result.validation_status,
                    evidence_ids=claim_result.evidence_ids,
                    reason=claim_result.reason,
                )
            )

        failed_claims = []
        for claim_result in evidence_results.failed_claims:
            failed_claims.append(
                ClaimValidationResult(
                    claim=claim_result.claim,
                    is_supported=False,
                    validator=claim_result.validator,
                    validation_status=claim_result.validation_status,
                    evidence_ids=claim_result.evidence_ids,
                    reason=claim_result.reason,
                    errors=claim_result.errors,
                )
            )

        unsupported_claims = []
        for claim_result in evidence_results.unsupported_claims:
            unsupported_claims.append(
                ClaimValidationResult(
                    claim=claim_result.claim,
                    is_supported=False,
                    validator=claim_result.validator,
                    validation_status=claim_result.validation_status,
                    evidence_ids=claim_result.evidence_ids,
                    reason=claim_result.reason,
                )
            )

        # Convert citation results — preserve validator
        citation_results_list = []
        for citation_result in citation_results.valid_citations:
            citation_results_list.append(
                CitationValidationResult(
                    citation=citation_result.citation,
                    is_valid=True,
                    validator=citation_result.validator,
                    validation_status=citation_result.validation_status,
                    reason=citation_result.reason,
                )
            )

        for citation_result in citation_results.invalid_citations:
            citation_results_list.append(
                CitationValidationResult(
                    citation=citation_result.citation,
                    is_valid=False,
                    validator=citation_result.validator,
                    validation_status=citation_result.validation_status,
                    reason=citation_result.reason,
                    errors=citation_result.errors,
                )
            )

        # Convert entity results — preserve validator
        validated_entities = []
        for entity_result in entity_results.validated_entities:
            validated_entities.append(
                EntityValidationResult(
                    entity_name=entity_result.entity_name,
                    entity_type=entity_result.entity_type,
                    is_valid=True,
                    validator=entity_result.validator,
                    validation_status=entity_result.validation_status,
                    reason=entity_result.reason,
                )
            )

        missing_entities = []
        for entity_result in entity_results.missing_entities:
            missing_entities.append(
                EntityValidationResult(
                    entity_name=entity_result.entity_name,
                    entity_type=entity_result.entity_type,
                    is_valid=False,
                    validator=entity_result.validator,
                    validation_status=entity_result.validation_status,
                    reason=entity_result.reason,
                    errors=entity_result.errors,
                )
            )

        # Convert relationship results — preserve validator
        validated_relationships = []
        for relationship_result in relationship_results.validated_relationships:
            validated_relationships.append(
                RelationshipValidationResult(
                    relationship=relationship_result.relationship,
                    is_valid=True,
                    validator=relationship_result.validator,
                    validation_status=relationship_result.validation_status,
                    reason=relationship_result.reason,
                )
            )

        failed_relationships = []
        for relationship_result in relationship_results.failed_relationships:
            failed_relationships.append(
                RelationshipValidationResult(
                    relationship=relationship_result.relationship,
                    is_valid=False,
                    validator=relationship_result.validator,
                    validation_status=relationship_result.validation_status,
                    reason=relationship_result.reason,
                    errors=relationship_result.errors,
                )
            )

        # Convert hallucination results — preserve validator
        hallucination_results_list = []
        for hallucination in hallucination_results.detected_hallucinations:
            hallucination_results_list.append(
                HallucinationResult(
                    fabricated_item=hallucination["item"],
                    item_type=hallucination["type"],
                    detected=True,
                    validator="HallucinationDetector",
                    reason=f"Fabricated {hallucination['type']}: {hallucination['item']}",
                )
            )

        # Create validation report
        validation_report = ValidationReport(
            validated_claims=validated_claims,
            failed_claims=failed_claims,
            unsupported_claims=unsupported_claims,
            validated_entities=validated_entities,
            missing_entities=missing_entities,
            validated_relationships=validated_relationships,
            failed_relationships=failed_relationships,
            citation_results=citation_results_list,
            hallucination_results=hallucination_results_list,
            confidence_breakdown=confidence_results.confidence_breakdown,
            processing_time=0.0,
            overall_status=confidence_results.validation_status,
        )

        return validation_report

    def _build_validated_response(
        self,
        diagnostic_response: DiagnosticResponse,
        validation_report: ValidationReport,
        evidence_results: EvidenceValidationResults,
        citation_results: CitationValidationResults,
        entity_results: EntityValidationResults,
        relationship_results: RelationshipValidationResults,
        safety_results: SafetyValidationResults,
        confidence_results: ConfidenceEngineResults,
    ) -> Any:
        """Build a validated diagnostic response."""
        from validation.models.validated_response import ValidatedDiagnosticResponse

        safety_warnings = []
        if not safety_results.is_safe:
            for warning in safety_results.missing_warnings:
                safety_warnings.append(f"SAFETY VIOLATION: {warning}")

        validated_response = ValidatedDiagnosticResponse(
            problem_summary=diagnostic_response.problem_summary,
            possible_causes=diagnostic_response.possible_causes,
            inspection_steps=diagnostic_response.inspection_steps,
            recommended_actions=diagnostic_response.recommended_actions,
            validated_entities=entity_results.validated_entities,
            validated_relationships=relationship_results.validated_relationships,
            validated_citations=citation_results.valid_citations,
            confidence=confidence_results.confidence_breakdown,
            safety_warnings=safety_warnings,
            validation_report=validation_report,
            metadata=diagnostic_response.metadata,
        )

        return validated_response

    def _build_metadata(
        self,
        diagnostic_response: DiagnosticResponse,
        validation_report: ValidationReport,
        confidence_results: ConfidenceEngineResults,
    ) -> Dict[str, Any]:
        """Build metadata for the validation results."""
        return {
            "timestamp": datetime.now().isoformat(),
            "confidence_threshold": self.config.confidence_threshold,
            "validation_strictness": self.config.validation_strictness,
            "original_response_type": "DiagnosticResponse",
            "validation_status": validation_report.overall_status,
            "overall_confidence": confidence_results.overall_score,
            "confidence_level": confidence_results.confidence_level,
            "num_validated_claims": len(validation_report.validated_claims),
            "num_failed_claims": len(validation_report.failed_claims),
            "num_unsupported_claims": len(validation_report.unsupported_claims),
            "num_missing_entities": len(validation_report.missing_entities),
            "num_failed_relationships": len(validation_report.failed_relationships),
            "num_hallucinations": len(validation_report.hallucination_results),
            "num_citations_total": len(validation_report.citation_results),
            "safety_violations": len([w for w in validation_report.hallucination_results if w.item_type == "safety"]),
            "completed_stages": validation_report.completed_stages,
            "failed_stages": validation_report.failed_stages,
        }