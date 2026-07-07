"""Reports and data structures for the Grounding & Validation Engine.

Contains:
- ValidationReport: Comprehensive validation results
- ClaimValidationResult: Results of claim validation
- CitationValidationResult: Results of citation validation
- EntityValidationResult: Results of entity validation
- RelationshipValidationResult: Results of relationship validation
- HallucinationResult: Hallucination detection results
- ConfidenceBreakdown: Confidence calculation breakdown
"""

from .validation_report import (
    ValidationReport,
    ClaimValidationResult,
    CitationValidationResult,
    EntityValidationResult,
    RelationshipValidationResult,
    HallucinationResult,
    ConfidenceBreakdown,
)
