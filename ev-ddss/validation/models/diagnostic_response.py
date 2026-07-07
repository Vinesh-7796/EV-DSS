from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class DiagnosticResponse:
    problem_summary: str = ""
    possible_causes: List[str] = field(default_factory=list)
    inspection_steps: List[str] = field(default_factory=list)
    recommended_actions: List[str] = field(default_factory=list)
    entities: Dict[str, List[str]] = field(default_factory=dict)
    relationships: List[str] = field(default_factory=list)
    citations: List[str] = field(default_factory=list)
    claims: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
