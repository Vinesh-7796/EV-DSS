"""LLM Orchestration Engine for EV-DDSS.

Technician Query + Structured Context Package → Intent Classification →
Context Optimization → Prompt Construction → Template Selection →
LLM Execution → Response Parsing → DiagnosticResponse

The engine performs reasoning exclusively on supplied context.
It never retrieves documents, accesses databases, or performs OCR.
"""

from reasoning.engine import ReasoningEngine
from reasoning.models.diagnostic_response import DiagnosticResponse
from reasoning.intent_classifier import IntentType

__all__ = [
    "ReasoningEngine",
    "DiagnosticResponse",
    "IntentType",
]
