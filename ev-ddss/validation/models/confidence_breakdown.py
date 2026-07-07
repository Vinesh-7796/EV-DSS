from dataclasses import dataclass

@dataclass
class ConfidenceBreakdown:
    evidence_coverage: float = 0.0
    citation_validity: float = 0.0
    retrieval_score: float = 0.0
    entity_validation: float = 0.0
    relationship_validation: float = 0.0
    consistency: float = 0.0
    hallucination_detection: float = 0.0

