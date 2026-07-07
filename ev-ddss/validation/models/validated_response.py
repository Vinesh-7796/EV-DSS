from dataclasses import dataclass, field
from typing import List, Dict, Any

from validation.models.validation_report import (
    ValidationReport,
    ConfidenceBreakdown,
    EntityValidationResult,
    RelationshipValidationResult,
    CitationValidationResult,
)

@dataclass
class ValidatedDiagnosticResponse:
    problem_summary: str = ""
    possible_causes: List[str] = field(default_factory=list)
    inspection_steps: List[str] = field(default_factory=list)
    recommended_actions: List[str] = field(default_factory=list)
    validated_entities: List[EntityValidationResult] = field(default_factory=list)
    validated_relationships: List[RelationshipValidationResult] = field(default_factory=list)
    validated_citations: List[CitationValidationResult] = field(default_factory=list)
    confidence: ConfidenceBreakdown = field(default_factory=ConfidenceBreakdown)
    safety_warnings: List[str] = field(default_factory=list)
    validation_report: ValidationReport = field(default_factory=ValidationReport)
    metadata: Dict[str, Any] = field(default_factory=dict)
