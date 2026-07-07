from dataclasses import dataclass, field
from typing import Dict, Any, List

@dataclass
class ValidationConfig:
    confidence_threshold: float = 0.85
    required_evidence_coverage: float = 0.9
    mandatory_citations: bool = True
    safety_rule_sets: List[str] = field(default_factory=lambda: ["high_voltage_ppe", "battery_isolation", "motor_power_off"])
    validation_strictness: str = "strict"
    hallucination_sensitivity: float = 0.0

    # Confidence weights (sum = 1.0)
    weight_evidence_coverage: float = 0.25
    weight_citation_validity: float = 0.15
    weight_retrieval_score: float = 0.15
    weight_entity_validation: float = 0.15
    weight_relationship_validation: float = 0.10
    weight_consistency: float = 0.10
    weight_hallucination_detection: float = 0.10

    # Penalty factors
    consistency_issue_penalty: float = 0.1
    hallucination_penalty: float = 0.2

    # Similarity thresholds
    warning_similarity_threshold: float = 0.7
    procedure_similarity_threshold: float = 0.7

    def to_dict(self) -> Dict[str, Any]:
        return {
            "confidence_threshold": self.confidence_threshold,
            "required_evidence_coverage": self.required_evidence_coverage,
            "mandatory_citations": self.mandatory_citations,
            "safety_rule_sets": self.safety_rule_sets,
            "validation_strictness": self.validation_strictness,
            "hallucination_sensitivity": self.hallucination_sensitivity,
            "weight_evidence_coverage": self.weight_evidence_coverage,
            "weight_citation_validity": self.weight_citation_validity,
            "weight_retrieval_score": self.weight_retrieval_score,
            "weight_entity_validation": self.weight_entity_validation,
            "weight_relationship_validation": self.weight_relationship_validation,
            "weight_consistency": self.weight_consistency,
            "weight_hallucination_detection": self.weight_hallucination_detection,
            "consistency_issue_penalty": self.consistency_issue_penalty,
            "hallucination_penalty": self.hallucination_penalty,
            "warning_similarity_threshold": self.warning_similarity_threshold,
            "procedure_similarity_threshold": self.procedure_similarity_threshold,
        }