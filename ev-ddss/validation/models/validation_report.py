from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class ClaimValidationResult:
    claim: str
    is_supported: bool
    validator: str = "EvidenceValidator"
    validation_status: str = "PASS"
    evidence_ids: List[str] = field(default_factory=list)
    reason: str = ""
    errors: List[str] = field(default_factory=list)

@dataclass
class CitationValidationResult:
    citation: str
    is_valid: bool
    validator: str = "CitationValidator"
    validation_status: str = "PASS"
    reason: str = ""
    errors: List[str] = field(default_factory=list)

@dataclass
class EntityValidationResult:
    entity_name: str
    entity_type: str
    is_valid: bool
    validator: str = "EntityValidator"
    validation_status: str = "PASS"
    reason: str = ""
    errors: List[str] = field(default_factory=list)

@dataclass
class RelationshipValidationResult:
    relationship: str
    is_valid: bool
    validator: str = "RelationshipValidator"
    validation_status: str = "PASS"
    reason: str = ""
    errors: List[str] = field(default_factory=list)

@dataclass
class HallucinationResult:
    fabricated_item: str
    item_type: str
    detected: bool
    validator: str = "HallucinationDetector"
    reason: str = ""

@dataclass
class ConfidenceBreakdown:
    evidence_coverage: float = 0.0
    citation_validity: float = 0.0
    retrieval_score: float = 0.0
    entity_validation: float = 0.0
    relationship_validation: float = 0.0
    consistency: float = 0.0
    hallucination_detection: float = 0.0

@dataclass
class StageResult:
    stage_name: str
    status: str = "PENDING"
    duration_ms: float = 0.0
    error: str = ""
    result_count: int = 0

@dataclass
class ValidationReport:
    validated_claims: List[ClaimValidationResult] = field(default_factory=list)
    failed_claims: List[ClaimValidationResult] = field(default_factory=list)
    unsupported_claims: List[ClaimValidationResult] = field(default_factory=list)
    validated_entities: List[EntityValidationResult] = field(default_factory=list)
    missing_entities: List[EntityValidationResult] = field(default_factory=list)
    validated_relationships: List[RelationshipValidationResult] = field(default_factory=list)
    failed_relationships: List[RelationshipValidationResult] = field(default_factory=list)
    citation_results: List[CitationValidationResult] = field(default_factory=list)
    hallucination_results: List[HallucinationResult] = field(default_factory=list)
    confidence_breakdown: ConfidenceBreakdown = field(default_factory=ConfidenceBreakdown)
    processing_time: float = 0.0
    overall_status: str = "PENDING"
    pipeline_stages: List[StageResult] = field(default_factory=list)
    completed_stages: List[str] = field(default_factory=list)
    failed_stages: List[str] = field(default_factory=list)
    stage_errors: Dict[str, str] = field(default_factory=dict)
    config_version: str = ""
    safety_rules_triggered: List[str] = field(default_factory=list)
    hallucination_summary: str = ""
