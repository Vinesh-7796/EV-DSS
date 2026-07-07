"""DiagnosticResponse — structured output model for the LLM Orchestration
Engine.

The LLM MUST return a JSON object conforming to this schema.
No free-form output is accepted.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class DiagnosticResponse(BaseModel):
    """Verified diagnostic response produced by the LLM orchestration engine.

    All fields must be present in the LLM's JSON output.  The response
    parser validates schema compliance after every LLM call.
    """

    problem_summary: str = Field(
        ..., min_length=1,
        description="Concise summary of the diagnosed problem.",
    )
    possible_causes: List[str] = Field(
        ..., min_length=1,
        description="Ordered list of possible causes (most likely first).",
    )
    inspection_steps: List[str] = Field(
        ..., min_length=1,
        description="Step-by-step inspection or test procedures.",
    )
    recommended_actions: List[str] = Field(
        ..., min_length=1,
        description="Recommended repair or corrective actions.",
    )
    referenced_entities: List[str] = Field(
        default_factory=list,
        description="Entity IDs referenced in the response (e.g. error codes, ECUs).",
    )
    referenced_documents: List[str] = Field(
        default_factory=list,
        description="Source documents referenced in the response.",
    )
    reasoning_summary: str = Field(
        default="",
        description="Brief explanation of how the conclusion was reached.",
    )
    citations: List[str] = Field(
        default_factory=list,
        description="Citation strings for evidence used in the response.",
    )
    related_components: List[str] = Field(
        default_factory=list,
        description="Component names related to this fault.",
    )
    connectors: List[str] = Field(
        default_factory=list,
        description="Connector IDs involved in the fault.",
    )
    fuses: List[str] = Field(
        default_factory=list,
        description="Fuse IDs involved in the fault.",
    )
    relays: List[str] = Field(
        default_factory=list,
        description="Relay IDs involved in the fault.",
    )
    can_signals: List[str] = Field(
        default_factory=list,
        description="CAN bus signal IDs involved in the fault.",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Processing metadata (model, latency, tokens, etc.).",
    )

    @field_validator("possible_causes")
    @classmethod
    def causes_not_empty(cls, v: List[str]) -> List[str]:
        if not v or all(not s.strip() for s in v):
            raise ValueError("At least one possible cause is required.")
        return v

    @field_validator("inspection_steps")
    @classmethod
    def steps_not_empty(cls, v: List[str]) -> List[str]:
        if not v or all(not s.strip() for s in v):
            raise ValueError("At least one inspection step is required.")
        return v

    @field_validator("recommended_actions")
    @classmethod
    def actions_not_empty(cls, v: List[str]) -> List[str]:
        if not v or all(not s.strip() for s in v):
            raise ValueError("At least one recommended action is required.")
        return v

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()

    @classmethod
    def example(cls) -> "DiagnosticResponse":
        """Return a minimal valid example (useful for tests / prompt
        demonstrations)."""
        return cls(
            problem_summary="Battery voltage below threshold.",
            possible_causes=["Faulty alternator", "Weak battery"],
            inspection_steps=["Measure voltage at terminals"],
            recommended_actions=["Replace alternator"],
            referenced_entities=["P0562"],
            referenced_documents=["BMS_Manual.pdf"],
            reasoning_summary="Voltage reading indicates charging system fault.",
            citations=["BMS_Manual.pdf p.42"],
            metadata={"model": "qwen3:8b", "latency_ms": 2500},
        )

    def summary(self) -> str:
        """One-line summary for logging."""
        causes = "; ".join(self.possible_causes[:2])
        return (
            f"problem={self.problem_summary[:80]} "
            f"causes=[{causes[:120]}] "
            f"entities={len(self.referenced_entities)} "
            f"docs={len(self.referenced_documents)}"
        )
