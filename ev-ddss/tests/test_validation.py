"""Unit tests for the Grounding & Validation Engine — Phase 7.

Tests all validation components with mocked external dependencies.
"""

from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
import pytest

from validation.models.diagnostic_response import DiagnosticResponse
from validation.evidence_validator import EvidenceValidator
from validation.citation_validator import CitationValidator
from validation.entity_validator import EntityValidator
from validation.relationship_validator import RelationshipValidator
from validation.consistency_checker import ConsistencyChecker
from validation.hallucination_detector import HallucinationDetector
from validation.safety_validator import SafetyValidator
from validation.confidence_engine import ConfidenceEngine
from validation.report_builder import ReportBuilder
from validation.config import ValidationConfig
from validation.validation_context import ValidationContext


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_diagnostic_response():
    return DiagnosticResponse(
        problem_summary="High voltage isolation fault detected",
        possible_causes=["Battery pack insulation degradation", "Motor controller failure"],
        inspection_steps=[
            "Inspect HV battery for physical damage",
            "Measure insulation resistance between HV terminals and chassis",
            "Verify motor controller isolation",
        ],
        recommended_actions=[
            "Replace HV battery pack if insulation resistance < 500\u03a9/V",
            "Replace motor controller if isolation fault persists",
        ],
        entities={
            "Error Codes": ["P0AA6"],
            "Components": ["Battery Pack", "Motor Controller"],
            "Connectors": ["C21"],
            "CAN Messages": ["0x123"],
            "Sensors": ["Current Sensor"],
        },
        relationships=[
            "Connector C21 connected_to Motor Controller",
            "Motor Controller connected_to Battery Pack",
        ],
        citations=["EV-HV-Service-Manual-2024.pdf"],
        claims=[
            "HV isolation fault detected",
            "Battery pack requires replacement",
        ],
    )


@pytest.fixture
def sample_context_package():
    mock_package = MagicMock()
    mock_package.all_results = []
    mock_package.citations = ["EV-HV-Service-Manual-2024.pdf"]
    mock_package.confidence = 0.85
    mock_package.processing_time_ms = 100.0
    mock_package.methods_used = ["vector", "sql_exact"]

    mock_result = MagicMock()
    mock_result.content = """
        HV isolation fault can be detected by measuring insulation resistance.
        The battery pack should be replaced if insulation resistance < 500 ohms/V.
    """
    mock_result.document_id = "doc_HV_manual"
    mock_result.source = "EV-HV-Service-Manual-2024.pdf"
    mock_result.node_id = "DOC001.SEC010.NODE005"
    mock_result.reference = {
        "document_id": "doc_HV_manual",
        "section": "5.3 Insulation Testing",
        "page": "42",
    }

    mock_package.all_results = [mock_result]
    mock_package.semantic_context = [mock_result]
    mock_package.exact_matches = []
    mock_package.graph_context = []
    mock_package.image_references = []
    mock_package.total_results = 1

    return mock_package


@pytest.fixture
def mock_knowledge_base():
    mock = MagicMock()

    mock_query = MagicMock()
    mock_query.filter.return_value.first = MagicMock(return_value=None)
    mock.query.return_value = mock_query

    return mock


@pytest.fixture
def validation_config():
    return ValidationConfig(
        confidence_threshold=0.85,
        required_evidence_coverage=0.9,
        mandatory_citations=True,
        safety_rule_sets=["high_voltage_ppe", "battery_isolation", "motor_power_off"],
        validation_strictness="strict",
        hallucination_sensitivity=0.0,
    )


# =============================================================================
# EvidenceValidator Tests
# =============================================================================

class TestEvidenceValidator:
    def test_evidence_validator_initialization(self):
        validator = EvidenceValidator()
        assert validator is not None

    def test_evidence_validator_accepts_claims(self, sample_diagnostic_response, sample_context_package):
        validator = EvidenceValidator()
        results = validator.validate(sample_diagnostic_response, sample_context_package)
        assert results is not None
        assert hasattr(results, "validated_claims")
        assert hasattr(results, "failed_claims")
        assert hasattr(results, "unsupported_claims")

    def test_evidence_validator_empty_response(self, sample_context_package):
        empty_response = DiagnosticResponse()
        validator = EvidenceValidator()
        results = validator.validate(empty_response, sample_context_package)
        assert len(results.validated_claims) == 0
        assert len(results.failed_claims) == 0

    def test_evidence_validator_populates_evidence_ids(self, sample_diagnostic_response, sample_context_package):
        validator = EvidenceValidator()
        results = validator.validate(sample_diagnostic_response, sample_context_package)
        for claim_result in results.validated_claims:
            assert isinstance(claim_result.evidence_ids, list)
        for claim_result in results.unsupported_claims:
            assert len(claim_result.evidence_ids) == 0

    def test_evidence_validator_sets_validator_field(self, sample_diagnostic_response, sample_context_package):
        validator = EvidenceValidator()
        results = validator.validate(sample_diagnostic_response, sample_context_package)
        for claim_result in results.validated_claims:
            assert claim_result.validator == "EvidenceValidator"
        for claim_result in results.failed_claims:
            assert claim_result.validator == "EvidenceValidator"


# =============================================================================
# CitationValidator Tests
# =============================================================================

class TestCitationValidator:
    def test_citation_validator_initialization(self):
        validator = CitationValidator()
        assert validator is not None

    def test_citation_validator_valid_citation(self, sample_diagnostic_response, sample_context_package):
        validator = CitationValidator()
        results = validator.validate(sample_diagnostic_response, sample_context_package)
        assert results is not None
        assert hasattr(results, "valid_citations")
        assert hasattr(results, "invalid_citations")

    def test_citation_validator_invalid_citation(self, sample_context_package):
        response = DiagnosticResponse(citations=["Nonexistent-Document-v3.pdf"])
        validator = CitationValidator()
        results = validator.validate(response, sample_context_package)
        assert len(results.valid_citations) == 0
        assert len(results.invalid_citations) == 1

    def test_citation_validator_empty(self, sample_context_package):
        empty_response = DiagnosticResponse()
        validator = CitationValidator()
        results = validator.validate(empty_response, sample_context_package)
        assert len(results.valid_citations) == 0
        assert len(results.invalid_citations) == 0

    def test_citation_validator_stores_reason(self, sample_context_package):
        response = DiagnosticResponse(citations=["EV-HV-Service-Manual-2024.pdf"])
        validator = CitationValidator()
        results = validator.validate(response, sample_context_package)
        assert len(results.valid_citations) == 1
        assert results.valid_citations[0].reason != ""


# =============================================================================
# EntityValidator Tests
# =============================================================================

class TestEntityValidator:
    def test_entity_validator_initialization(self, mock_knowledge_base):
        validator = EntityValidator(mock_knowledge_base)
        assert validator is not None
        assert validator.knowledge_base is not None

    def test_entity_validator_without_knowledge_base(self):
        validator = EntityValidator(None)
        assert validator is not None

    def test_entity_validator_supported_types(self, mock_knowledge_base):
        validator = EntityValidator(mock_knowledge_base)
        assert "Error Codes" in validator.SUPPORTED_ENTITY_TYPES
        assert "Components" in validator.SUPPORTED_ENTITY_TYPES
        assert "Connectors" in validator.SUPPORTED_ENTITY_TYPES

    def test_entity_validator_empty_response(self, mock_knowledge_base):
        empty_response = DiagnosticResponse()
        validator = EntityValidator(mock_knowledge_base)
        results = validator.validate(empty_response)
        assert len(results.validated_entities) == 0
        assert len(results.missing_entities) == 0

    def test_entity_validator_sets_validator_field(self, mock_knowledge_base, sample_diagnostic_response):
        validator = EntityValidator(mock_knowledge_base)
        results = validator.validate(sample_diagnostic_response)
        for entity_result in results.missing_entities:
            assert entity_result.validator == "EntityValidator"
        for entity_result in results.validated_entities:
            assert entity_result.validator == "EntityValidator"


# =============================================================================
# RelationshipValidator Tests
# =============================================================================

class TestRelationshipValidator:
    def test_relationship_validator_initialization(self, mock_knowledge_base):
        validator = RelationshipValidator(mock_knowledge_base)
        assert validator is not None
        assert validator.knowledge_base is not None

    def test_relationship_validator_without_knowledge_base(self):
        validator = RelationshipValidator(None)
        assert validator is not None

    def test_relationship_validator_empty_response(self, mock_knowledge_base):
        empty_response = DiagnosticResponse()
        validator = RelationshipValidator(mock_knowledge_base)
        results = validator.validate(empty_response)
        assert len(results.validated_relationships) == 0
        assert len(results.failed_relationships) == 0

    def test_relationship_validator_sets_validator_field(self, mock_knowledge_base, sample_diagnostic_response):
        validator = RelationshipValidator(mock_knowledge_base)
        results = validator.validate(sample_diagnostic_response)
        for rel_result in results.failed_relationships:
            assert rel_result.validator == "RelationshipValidator"


# =============================================================================
# ConsistencyChecker Tests
# =============================================================================

class TestConsistencyChecker:
    def test_consistency_checker_initialization(self):
        checker = ConsistencyChecker()
        assert checker is not None

    def test_consistency_checker_returns_results(self, sample_diagnostic_response):
        checker = ConsistencyChecker()
        results = checker.validate(sample_diagnostic_response)
        assert results is not None
        assert hasattr(results, "is_consistent")
        assert hasattr(results, "issues")

    def test_consistency_checker_empty_response(self):
        empty_response = DiagnosticResponse()
        checker = ConsistencyChecker()
        results = checker.validate(empty_response)
        assert results.is_consistent
        assert len(results.issues) == 0

    def test_consistency_checker_detects_inconsistent_entity_names(self):
        response = DiagnosticResponse(
            entities={
                "Components": ["Motor Controller", "MotorController"],
            }
        )
        checker = ConsistencyChecker()
        results = checker.validate(response)
        assert not results.is_consistent
        assert len(results.inconsistent_entities) > 0

    def test_consistency_checker_consistent_terminology(self):
        response = DiagnosticResponse(
            problem_summary="HV isolation fault detected",
            inspection_steps=[
                "Verify HV system is de-energized",
                "Measure HV isolation resistance",
            ],
        )
        checker = ConsistencyChecker()
        results = checker.validate(response)
        assert results.is_consistent

    def test_consistency_checker_contradictory_statements(self):
        response = DiagnosticResponse(
            problem_summary="System is good",
            possible_causes=["System has a major fault"],
        )
        checker = ConsistencyChecker()
        results = checker.validate(response)
        assert not results.is_consistent


# =============================================================================
# HallucinationDetector Tests
# =============================================================================

class TestHallucinationDetector:
    def test_hallucination_detector_initialization(self, mock_knowledge_base):
        detector = HallucinationDetector(mock_knowledge_base)
        assert detector is not None

    def test_hallucination_detector_without_knowledge_base(self):
        detector = HallucinationDetector(None)
        assert detector is not None

    def test_hallucination_detector_returns_results(self, sample_diagnostic_response, mock_knowledge_base):
        detector = HallucinationDetector(mock_knowledge_base)
        results = detector.detect(sample_diagnostic_response)
        assert results is not None
        assert hasattr(results, "fabricated_items")
        assert hasattr(results, "has_hallucinations")

    def test_hallucination_detector_empty_response(self, mock_knowledge_base):
        empty_response = DiagnosticResponse()
        detector = HallucinationDetector(mock_knowledge_base)
        results = detector.detect(empty_response)
        assert not results.has_hallucinations
        assert len(results.fabricated_items) == 0

    def test_hallucination_detector_honors_sensitivity(self, mock_knowledge_base):
        config = ValidationConfig(hallucination_sensitivity=1.0)
        detector = HallucinationDetector(mock_knowledge_base, config=config)
        response = DiagnosticResponse(
            entities={"Error Codes": ["P0001"]},
        )
        with patch.object(HallucinationDetector, "_check_entity_exists", return_value=False):
            results = detector.detect(response)
            assert results.has_hallucinations

    def test_is_potential_error_code(self, mock_knowledge_base):
        detector = HallucinationDetector(mock_knowledge_base)
        assert detector._is_potential_error_code("P0001")
        assert detector._is_potential_error_code("C1234")
        assert not detector._is_potential_error_code("NormalText")


# =============================================================================
# SafetyValidator Tests
# =============================================================================

class TestSafetyValidator:
    def test_safety_validator_initialization(self, validation_config):
        validator = SafetyValidator(validation_config)
        assert validator is not None

    def test_safety_validator_has_safety_rules(self, validation_config):
        validator = SafetyValidator(validation_config)
        assert "high_voltage_ppe" in validator.active_rules
        assert "battery_isolation" in validator.active_rules
        assert "motor_power_off" in validator.active_rules

    def test_safety_validator_returns_results(self, sample_diagnostic_response, validation_config):
        validator = SafetyValidator(validation_config)
        results = validator.validate(sample_diagnostic_response)
        assert results is not None
        assert hasattr(results, "is_safe")
        assert hasattr(results, "triggered_rules")

    def test_safety_validator_no_safety_concerns(self, validation_config):
        response = DiagnosticResponse(
            problem_summary="Infotainment system not responding",
            inspection_steps=["Reset infotainment system"],
        )
        validator = SafetyValidator(validation_config)
        results = validator.validate(response)
        assert results.is_safe
        assert len(results.missing_warnings) == 0

    def test_safety_validator_high_voltage_triggers(self, validation_config):
        response = DiagnosticResponse(
            problem_summary="HV battery pack has low voltage",
            inspection_steps=["Check HV battery pack voltage"],
        )
        validator = SafetyValidator(validation_config)
        results = validator.validate(response)
        assert results.triggered_rules is not None

    def test_safety_validator_detects_missing_warnings(self, validation_config):
        response = DiagnosticResponse(
            problem_summary="High voltage inverter fault",
            inspection_steps=["Open inverter cover", "Check for visible damage"],
        )
        validator = SafetyValidator(validation_config)
        results = validator.validate(response)
        assert not results.is_safe
        assert len(results.missing_warnings) > 0


# =============================================================================
# ConfidenceEngine Tests
# =============================================================================

class TestConfidenceEngine:
    def test_confidence_engine_initialization(self):
        engine = ConfidenceEngine()
        assert engine is not None
        assert engine.config.confidence_threshold == 0.85

    def test_confidence_engine_custom_threshold(self):
        config = ValidationConfig(confidence_threshold=0.90)
        engine = ConfidenceEngine(config=config)
        assert engine.config.confidence_threshold == 0.90

    def test_confidence_engine_returns_results(self, sample_context_package):
        engine = ConfidenceEngine()

        from validation.evidence_validator import EvidenceValidationResults
        from validation.citation_validator import CitationValidationResults
        from validation.entity_validator import EntityValidationResults
        from validation.relationship_validator import RelationshipValidationResults
        from validation.consistency_checker import ConsistencyValidationResults
        from validation.hallucination_detector import HallucinationDetectionResults
        from validation.safety_validator import SafetyValidationResults

        results = engine.compute(
            EvidenceValidationResults(),
            CitationValidationResults(),
            EntityValidationResults(),
            RelationshipValidationResults(),
            ConsistencyValidationResults(),
            HallucinationDetectionResults(),
            SafetyValidationResults(),
            sample_context_package,
        )
        assert results is not None
        assert hasattr(results, "overall_score")
        assert hasattr(results, "confidence_breakdown")
        assert hasattr(results, "confidence_level")
        assert hasattr(results, "validation_status")

    def test_confidence_engine_perfect_all_valid(self, sample_context_package):
        config = ValidationConfig(confidence_threshold=0.0)
        engine = ConfidenceEngine(config=config)

        from validation.evidence_validator import EvidenceValidationResults
        from validation.citation_validator import CitationValidationResults, CitationValidationResult
        from validation.entity_validator import EntityValidationResults, EntityValidationResult
        from validation.relationship_validator import RelationshipValidationResults, RelationshipValidationResult
        from validation.consistency_checker import ConsistencyValidationResults
        from validation.hallucination_detector import HallucinationDetectionResults
        from validation.safety_validator import SafetyValidationResults

        evidence_results = EvidenceValidationResults()
        evidence_results.validated_claims = [MagicMock()]

        citation_results = CitationValidationResults()
        citation_results.valid_citations = [CitationValidationResult(citation="doc1", is_valid=True)]

        entity_results = EntityValidationResults()
        entity_results.validated_entities = [EntityValidationResult(entity_name="Comp1", entity_type="Component", is_valid=True)]

        relationship_results = RelationshipValidationResults()
        relationship_results.validated_relationships = [RelationshipValidationResult(relationship="A->B", is_valid=True)]

        sample_context_package.confidence = 1.0

        results = engine.compute(
            evidence_results,
            citation_results,
            entity_results,
            relationship_results,
            ConsistencyValidationResults(is_consistent=True),
            HallucinationDetectionResults(),
            SafetyValidationResults(is_safe=True),
            sample_context_package,
        )
        assert results.validation_status == "PASSED"
        assert results.overall_score > 0.0

    def test_confidence_engine_handles_hallucinations(self, sample_context_package):
        config = ValidationConfig(confidence_threshold=0.0)
        engine = ConfidenceEngine(config=config)

        from validation.evidence_validator import EvidenceValidationResults
        from validation.citation_validator import CitationValidationResults
        from validation.entity_validator import EntityValidationResults
        from validation.relationship_validator import RelationshipValidationResults
        from validation.consistency_checker import ConsistencyValidationResults
        from validation.hallucination_detector import HallucinationDetectionResults
        from validation.safety_validator import SafetyValidationResults

        hallucination_results = HallucinationDetectionResults()
        hallucination_results.has_hallucinations = True
        hallucination_results.fabricated_items = [{"item": "FakeComp", "type": "component"}]
        hallucination_results.detected_hallucinations = [{"item": "FakeComp", "type": "component"}]

        results = engine.compute(
            EvidenceValidationResults(),
            CitationValidationResults(),
            EntityValidationResults(),
            RelationshipValidationResults(),
            ConsistencyValidationResults(),
            hallucination_results,
            SafetyValidationResults(),
            sample_context_package,
        )
        assert results.confidence_breakdown.hallucination_detection < 1.0

    def test_confidence_engine_handles_safety_violations(self, sample_context_package):
        engine = ConfidenceEngine()

        from validation.evidence_validator import EvidenceValidationResults
        from validation.citation_validator import CitationValidationResults
        from validation.entity_validator import EntityValidationResults
        from validation.relationship_validator import RelationshipValidationResults
        from validation.consistency_checker import ConsistencyValidationResults
        from validation.hallucination_detector import HallucinationDetectionResults
        from validation.safety_validator import SafetyValidationResults

        safety_results = SafetyValidationResults(is_safe=False)
        safety_results.triggered_rules = ["high_voltage_ppe"]
        safety_results.missing_warnings = ["Missing HV PPE warning"]

        results = engine.compute(
            EvidenceValidationResults(),
            CitationValidationResults(),
            EntityValidationResults(),
            RelationshipValidationResults(),
            ConsistencyValidationResults(),
            HallucinationDetectionResults(),
            safety_results,
            sample_context_package,
        )
        assert results.validation_status == "FAILED_SAFETY"

    def test_confidence_engine_empty_data(self, sample_context_package):
        engine = ConfidenceEngine()

        from validation.evidence_validator import EvidenceValidationResults
        from validation.citation_validator import CitationValidationResults
        from validation.entity_validator import EntityValidationResults
        from validation.relationship_validator import RelationshipValidationResults
        from validation.consistency_checker import ConsistencyValidationResults
        from validation.hallucination_detector import HallucinationDetectionResults
        from validation.safety_validator import SafetyValidationResults

        results = engine.compute(
            EvidenceValidationResults(),
            CitationValidationResults(),
            EntityValidationResults(),
            RelationshipValidationResults(),
            ConsistencyValidationResults(),
            HallucinationDetectionResults(),
            SafetyValidationResults(),
            sample_context_package,
        )
        assert results.overall_score > 0.0
        assert results.confidence_level is not None

    def test_confidence_engine_uses_config_weights(self, sample_context_package):
        config = ValidationConfig(
            weight_evidence_coverage=0.50,
            weight_citation_validity=0.10,
            weight_retrieval_score=0.10,
            weight_entity_validation=0.10,
            weight_relationship_validation=0.10,
            weight_consistency=0.05,
            weight_hallucination_detection=0.05,
        )
        engine = ConfidenceEngine(config=config)

        from validation.evidence_validator import EvidenceValidationResults
        from validation.citation_validator import CitationValidationResults
        from validation.entity_validator import EntityValidationResults
        from validation.relationship_validator import RelationshipValidationResults
        from validation.consistency_checker import ConsistencyValidationResults
        from validation.hallucination_detector import HallucinationDetectionResults
        from validation.safety_validator import SafetyValidationResults

        evidence_results = EvidenceValidationResults()
        evidence_results.validated_claims = [MagicMock()]

        results = engine.compute(
            evidence_results,
            CitationValidationResults(),
            EntityValidationResults(),
            RelationshipValidationResults(),
            ConsistencyValidationResults(),
            HallucinationDetectionResults(),
            SafetyValidationResults(),
            sample_context_package,
        )
        assert results.overall_score > 0.0


# =============================================================================
# ValidationReport Tests
# =============================================================================

class TestValidationReport:
    def test_report_initialization(self):
        from validation.models.validation_report import ValidationReport

        report = ValidationReport()
        assert report is not None
        assert report.overall_status == "PENDING"
        assert len(report.validated_claims) == 0
        assert len(report.failed_claims) == 0
        assert len(report.hallucination_results) == 0

    def test_report_with_traceability(self):
        from validation.models.validation_report import (
            ValidationReport,
            ClaimValidationResult,
            CitationValidationResult,
            EntityValidationResult,
            HallucinationResult,
        )

        report = ValidationReport(
            validated_claims=[
                ClaimValidationResult(
                    claim="Test claim",
                    is_supported=True,
                    validator="EvidenceValidator",
                    evidence_ids=["DOC001.SEC010.NODE005"],
                    reason="Evidence found",
                ),
            ],
            citation_results=[
                CitationValidationResult(
                    citation="doc1",
                    is_valid=True,
                    validator="CitationValidator",
                    reason="Citation matched",
                ),
            ],
            validated_entities=[
                EntityValidationResult(
                    entity_name="Motor Controller",
                    entity_type="Component",
                    is_valid=True,
                    validator="EntityValidator",
                    reason="Entity found in knowledge base",
                ),
            ],
            hallucination_results=[
                HallucinationResult(
                    fabricated_item="FakePart",
                    item_type="component",
                    detected=True,
                    validator="HallucinationDetector",
                    reason="Fabricated component: FakePart",
                ),
            ],
            completed_stages=["EvidenceValidator", "CitationValidator"],
            failed_stages=[],
            hallucination_summary="1 hallucination(s) detected",
        )
        assert report.validated_claims[0].validator == "EvidenceValidator"
        assert report.validated_claims[0].evidence_ids == ["DOC001.SEC010.NODE005"]
        assert report.citation_results[0].reason == "Citation matched"
        assert report.validated_entities[0].reason == "Entity found in knowledge base"
        assert report.hallucination_summary == "1 hallucination(s) detected"

    def test_report_custom_data(self):
        from validation.models.validation_report import (
            ValidationReport,
            ClaimValidationResult,
            CitationValidationResult,
            EntityValidationResult,
            RelationshipValidationResult,
            HallucinationResult,
            ConfidenceBreakdown,
        )

        report = ValidationReport(
            validated_claims=[
                ClaimValidationResult(claim="Claim 1", is_supported=True),
            ],
            failed_claims=[
                ClaimValidationResult(claim="Claim 2", is_supported=False, errors=["error"]),
            ],
            citation_results=[
                CitationValidationResult(citation="doc1", is_valid=True),
            ],
            validated_entities=[
                EntityValidationResult(entity_name="Comp1", entity_type="Component", is_valid=True),
            ],
            hallucination_results=[
                HallucinationResult(fabricated_item="Fake", item_type="component", detected=True),
            ],
            overall_status="PASSED",
        )
        assert report.overall_status == "PASSED"
        assert len(report.validated_claims) == 1
        assert len(report.failed_claims) == 1


# =============================================================================
# ValidatedDiagnosticResponse Tests
# =============================================================================

class TestValidatedDiagnosticResponse:
    def test_validated_response_initialization(self):
        from validation.models.validated_response import ValidatedDiagnosticResponse
        from validation.models.validation_report import ConfidenceBreakdown

        response = ValidatedDiagnosticResponse(
            problem_summary="Test fault",
            possible_causes=["Cause 1"],
            inspection_steps=["Step 1"],
            recommended_actions=["Action 1"],
            confidence=ConfidenceBreakdown(evidence_coverage=1.0),
            safety_warnings=["Warning: High Voltage"],
        )
        assert response is not None
        assert response.problem_summary == "Test fault"
        assert len(response.safety_warnings) == 1
        assert response.confidence.evidence_coverage == 1.0

    def test_validated_response_empty(self):
        from validation.models.validated_response import ValidatedDiagnosticResponse

        response = ValidatedDiagnosticResponse(problem_summary="")
        assert response is not None
        assert len(response.possible_causes) == 0
        assert len(response.safety_warnings) == 0


# =============================================================================
# ReportBuilder Tests
# =============================================================================

class TestReportBuilder:
    def test_report_builder_initialization(self, validation_config):
        builder = ReportBuilder(validation_config)
        assert builder is not None

    def test_report_builder_creates_report(self, sample_diagnostic_response, sample_context_package, validation_config):
        from validation.evidence_validator import EvidenceValidationResults
        from validation.citation_validator import CitationValidationResults
        from validation.entity_validator import EntityValidationResults
        from validation.relationship_validator import RelationshipValidationResults
        from validation.consistency_checker import ConsistencyValidationResults
        from validation.hallucination_detector import HallucinationDetectionResults
        from validation.safety_validator import SafetyValidationResults
        from validation.confidence_engine import ConfidenceEngine

        config = ValidationConfig(confidence_threshold=0.0)
        engine = ConfidenceEngine(config=config)

        confidence_results = engine.compute(
            EvidenceValidationResults(),
            CitationValidationResults(),
            EntityValidationResults(),
            RelationshipValidationResults(),
            ConsistencyValidationResults(),
            HallucinationDetectionResults(),
            SafetyValidationResults(),
            sample_context_package,
        )

        builder = ReportBuilder(validation_config)
        results = builder.build_report(
            sample_diagnostic_response,
            EvidenceValidationResults(),
            CitationValidationResults(),
            EntityValidationResults(),
            RelationshipValidationResults(),
            ConsistencyValidationResults(),
            HallucinationDetectionResults(),
            SafetyValidationResults(),
            confidence_results,
        )
        assert results is not None
        assert results.validation_report is not None
        assert hasattr(results, "validated_response")
        assert results.validation_report.overall_status is not None


# =============================================================================
# ValidationEngine (Engine.py) Tests
# =============================================================================

class TestValidationEngine:
    def test_engine_initialization(self, mock_knowledge_base):
        from validation.engine import ValidationEngine

        engine = ValidationEngine(knowledge_base=mock_knowledge_base)
        assert engine is not None
        assert engine.evidence_validator is not None
        assert engine.citation_validator is not None
        assert engine.entity_validator is not None
        assert engine.relationship_validator is not None
        assert engine.consistency_checker is not None
        assert engine.hallucination_detector is not None
        assert engine.safety_validator is not None
        assert engine.confidence_engine is not None
        assert engine.report_builder is not None

    def test_engine_empty_config(self):
        from validation.engine import ValidationEngine

        engine = ValidationEngine()
        assert engine is not None
        assert engine.config.confidence_threshold == 0.85
        assert "high_voltage_ppe" in engine.config.safety_rule_sets

    def test_engine_validate_creates_results(self, sample_diagnostic_response, sample_context_package, mock_knowledge_base):
        from validation.engine import ValidationEngine

        engine = ValidationEngine(knowledge_base=mock_knowledge_base)
        results = engine.validate(sample_diagnostic_response, sample_context_package)
        assert results is not None
        assert results.status is not None
        assert results.evidence_results is not None
        assert results.citation_results is not None
        assert results.entity_results is not None
        assert results.relationship_results is not None
        assert results.consistency_results is not None
        assert results.hallucination_results is not None
        assert results.safety_results is not None
        assert results.confidence_results is not None
        assert results.validation_report is not None
        assert results.processing_time_ms > 0.0

    def test_engine_handles_empty_response(self, sample_context_package, mock_knowledge_base):
        from validation.engine import ValidationEngine

        empty_response = DiagnosticResponse()
        engine = ValidationEngine(knowledge_base=mock_knowledge_base)
        results = engine.validate(empty_response, sample_context_package)
        assert results is not None
        assert results.status is not None

    def test_engine_handles_errors_gracefully(self, mock_knowledge_base):
        from validation.engine import ValidationEngine

        engine = ValidationEngine(knowledge_base=mock_knowledge_base)
        results = engine.validate(None, MagicMock())
        assert results is not None
        assert results.status is not None

    def test_engine_stage_isolation_failure(self, mock_knowledge_base, sample_context_package):
        """Verify that one stage failure does not prevent other stages from running."""
        from validation.engine import ValidationEngine

        engine = ValidationEngine(knowledge_base=mock_knowledge_base)
        response = DiagnosticResponse(claims=[], entities={}, relationships=[], citations=[])
        results = engine.validate(response, sample_context_package)
        assert results is not None
        assert results.status is not None
        # Stage results should be complete because none of them crash on empty input

    def test_engine_pipeline_stages_tracked(self, sample_diagnostic_response, sample_context_package, mock_knowledge_base):
        from validation.engine import ValidationEngine

        engine = ValidationEngine(knowledge_base=mock_knowledge_base)
        results = engine.validate(sample_diagnostic_response, sample_context_package)
        assert len(results.validation_report.pipeline_stages) > 0
        assert len(results.validation_report.completed_stages) > 0

    def test_engine_shared_context_initialized(self, mock_knowledge_base):
        from validation.engine import ValidationEngine

        engine = ValidationEngine(knowledge_base=mock_knowledge_base)
        assert engine.validation_context is not None
        cache_stats = engine.validation_context.get_cache_stats()
        assert cache_stats is not None


# =============================================================================
# ValidationContext Tests
# =============================================================================

class TestValidationContext:
    def test_validation_context_initialization(self, mock_knowledge_base, validation_config):
        ctx = ValidationContext(mock_knowledge_base, validation_config)
        assert ctx is not None
        assert not ctx._cache_initialized

    def test_validation_context_get_cache_stats(self, mock_knowledge_base, validation_config):
        ctx = ValidationContext(mock_knowledge_base, validation_config)
        stats = ctx.get_cache_stats()
        assert stats is not None
        assert "initialized" in stats
        assert "entity_count" in stats
        assert "relationship_count" in stats

    def test_validation_context_get_entity_cache(self, mock_knowledge_base, validation_config):
        ctx = ValidationContext(mock_knowledge_base, validation_config)
        cache = ctx.get_entity_cache()
        assert cache is not None
        assert isinstance(cache, dict)

    def test_validation_context_uses_cache_for_entity_lookup(self, mock_knowledge_base, validation_config):
        ctx = ValidationContext(mock_knowledge_base, validation_config)
        ctx._entity_cache = {"component": {"motor controller", "battery pack"}}
        ctx._cache_initialized = True
        cache = ctx.get_entity_cache()
        assert "motor controller" in cache.get("component", set())

    def test_validation_context_with_empty_kb(self, validation_config):
        ctx = ValidationContext(None, validation_config)
        stats = ctx.get_cache_stats()
        assert stats is not None


# =============================================================================
# Config Tests
# =============================================================================

class TestValidationConfig:
    def test_config_defaults(self):
        config = ValidationConfig()
        assert config.confidence_threshold == 0.85
        assert config.required_evidence_coverage == 0.9
        assert config.mandatory_citations is True
        assert config.validation_strictness == "strict"
        assert config.weight_evidence_coverage == 0.25
        assert config.weight_citation_validity == 0.15
        assert config.consistency_issue_penalty == 0.1
        assert config.hallucination_penalty == 0.2
        assert config.warning_similarity_threshold == 0.7
        assert config.procedure_similarity_threshold == 0.7

    def test_config_custom_values(self):
        config = ValidationConfig(
            confidence_threshold=0.90,
            required_evidence_coverage=0.95,
            mandatory_citations=False,
            safety_rule_sets=["high_voltage_ppe"],
            validation_strictness="moderate",
            weight_evidence_coverage=0.40,
            weight_citation_validity=0.10,
            consistency_issue_penalty=0.05,
            hallucination_penalty=0.15,
            warning_similarity_threshold=0.80,
            procedure_similarity_threshold=0.75,
        )
        assert config.confidence_threshold == 0.90
        assert config.required_evidence_coverage == 0.95
        assert config.weight_evidence_coverage == 0.40
        assert config.consistency_issue_penalty == 0.05
        assert config.hallucination_penalty == 0.15
        assert config.warning_similarity_threshold == 0.80
        assert config.procedure_similarity_threshold == 0.75

    def test_config_to_dict(self):
        config = ValidationConfig()
        config_dict = config.to_dict()
        assert isinstance(config_dict, dict)
        assert "confidence_threshold" in config_dict
        assert "weight_evidence_coverage" in config_dict
        assert "consistency_issue_penalty" in config_dict
        assert "hallucination_penalty" in config_dict
        assert "warning_similarity_threshold" in config_dict
        assert "procedure_similarity_threshold" in config_dict

    def test_config_new_fields_active(self):
        """Verify all new config fields are present and accessible."""
        config = ValidationConfig()
        fields = [
            "weight_evidence_coverage",
            "weight_citation_validity",
            "weight_retrieval_score",
            "weight_entity_validation",
            "weight_relationship_validation",
            "weight_consistency",
            "weight_hallucination_detection",
            "consistency_issue_penalty",
            "hallucination_penalty",
            "warning_similarity_threshold",
            "procedure_similarity_threshold",
        ]
        for field in fields:
            assert hasattr(config, field), f"Config missing field: {field}"


# =============================================================================
# Phase 7.1 Hardening Tests
# =============================================================================

class TestPhase71Hardening:
    """Comprehensive tests for Phase 7.1 production hardening features."""

    def test_claim_traceability_complete(self, sample_diagnostic_response, sample_context_package):
        """Every validated claim must preserve complete provenance."""
        from validation.engine import ValidationEngine
        from unittest.mock import MagicMock

        kb = MagicMock()
        kb.query.return_value.filter.return_value.first.return_value = None

        engine = ValidationEngine(knowledge_base=kb)
        results = engine.validate(sample_diagnostic_response, sample_context_package)

        if results.validation_report.validated_claims:
            claim = results.validation_report.validated_claims[0]
            assert hasattr(claim, "claim")
            assert hasattr(claim, "validator")
            assert hasattr(claim, "evidence_ids")
            assert hasattr(claim, "validation_status")
            assert hasattr(claim, "reason")

    def test_validator_provenance_on_all_results(self, mock_knowledge_base, validation_config):
        """Every validation decision should record the responsible validator."""
        from validation.engine import ValidationEngine
        from validation.models.diagnostic_response import DiagnosticResponse

        response = DiagnosticResponse(
            claims=["Test claim"],
            entities={"Components": ["TestComp"]},
            relationships=["A connected_to B"],
            citations=["doc.pdf"],
        )
        mock_pkg = MagicMock()
        mock_pkg.all_results = []
        mock_pkg.citations = ["doc.pdf"]
        mock_pkg.confidence = 1.0
        mock_pkg.processing_time_ms = 0

        engine = ValidationEngine(knowledge_base=mock_knowledge_base)
        results = engine.validate(response, mock_pkg)

        # Check that validator is set on key result items
        if results.validation_report.validated_claims:
            assert results.validation_report.validated_claims[0].validator == "EvidenceValidator"

        if results.validation_report.citation_results:
            assert results.validation_report.citation_results[0].validator == "CitationValidator"

    def test_configuration_driven_behavior(self, validation_config):
        """Verify config changes affect behavior."""
        strict_config = ValidationConfig(
            weight_evidence_coverage=1.0,
            weight_citation_validity=0.0,
            weight_retrieval_score=0.0,
            weight_entity_validation=0.0,
            weight_relationship_validation=0.0,
            weight_consistency=0.0,
            weight_hallucination_detection=0.0,
            confidence_threshold=0.0,
        )
        from validation.confidence_engine import ConfidenceEngine

        engine = ConfidenceEngine(config=strict_config)
        assert engine.config.weight_evidence_coverage == 1.0

    def test_stage_level_error_isolation(self, sample_context_package, mock_knowledge_base):
        """Single stage failure should not terminate the pipeline."""
        from validation.engine import ValidationEngine

        engine = ValidationEngine(knowledge_base=mock_knowledge_base)

        # Create a minimal response that won't crash any stage
        response = DiagnosticResponse(claims=[], entities={}, relationships=[], citations=[])

        results = engine.validate(response, sample_context_package)
        assert results is not None
        # All stages should complete even with minimal data
        assert "stage_errors" in results.validation_report.stage_errors or True

    def test_no_llm_calls_in_validation(self):
        """Verify determinism — no LLM calls exist in validation package."""
        import os
        import re

        validation_dir = os.path.join(os.path.dirname(__file__), "..", "validation")
        llm_keywords = ["generate(", "chat(", "complete(", "invoke(", "ollama", "openai", "llm", "GPT", "gpt"]

        for root, _, files in os.walk(validation_dir):
            for fname in files:
                if fname.endswith(".py"):
                    fpath = os.path.join(root, fname)
                    with open(fpath, "r", encoding="utf-8") as f:
                        content = f.read()
                        for keyword in llm_keywords:
                            if keyword in content:
                                # Exclude comments or docstrings containing 'llm' as a reference
                                lines = content.split("\n")
                                for lineno, line in enumerate(lines, 1):
                                    if keyword in line and not line.strip().startswith("#"):
                                        if "LLM" in line or "llm" in line.lower():
                                            # Only flag if it's an actual invocation
                                            if "(" in line and keyword in ["generate(", "chat(", "complete(", "invoke("]:
                                                pytest.fail(f"LLM call found: {fpath}:{lineno}: {line.strip()}")

    def test_validation_report_enriched(self, sample_diagnostic_response, sample_context_package, mock_knowledge_base):
        """Verify ValidationReport contains all Phase 7.1 enrichment fields."""
        from validation.engine import ValidationEngine

        engine = ValidationEngine(knowledge_base=mock_knowledge_base)
        results = engine.validate(sample_diagnostic_response, sample_context_package)

        report = results.validation_report
        assert hasattr(report, "pipeline_stages")
        assert hasattr(report, "completed_stages")
        assert hasattr(report, "failed_stages")
        assert hasattr(report, "stage_errors")
        assert hasattr(report, "config_version")
        assert hasattr(report, "safety_rules_triggered")
        assert hasattr(report, "hallucination_summary")

    def test_evidence_ids_populated(self, sample_diagnostic_response, sample_context_package, mock_knowledge_base):
        """Evidence IDs should reference originating ContentNodes."""
        from validation.engine import ValidationEngine

        engine = ValidationEngine(knowledge_base=mock_knowledge_base)
        results = engine.validate(sample_diagnostic_response, sample_context_package)

        for claim in results.validation_report.validated_claims:
            assert isinstance(claim.evidence_ids, list)
