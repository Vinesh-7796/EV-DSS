"""Intent Classifier — detects the technician's diagnostic intent from
their natural-language query.

Uses keyword / pattern matching (no LLM call) so that template selection
happens before any generation.
"""

from enum import Enum
from typing import List, Optional, Tuple


class IntentType(str, Enum):
    """Supported diagnostic intents — each maps to a prompt template."""

    ERROR_CODE = "error_code"
    COMPONENT = "component"
    CAN_SIGNAL = "can_signal"
    CONNECTOR = "connector"
    PROCEDURE = "procedure"
    MAINTENANCE = "maintenance"
    SPECIFICATION = "specification"
    COMPARISON = "comparison"
    GENERAL = "general"

    def __str__(self) -> str:
        return self.value


# ── Keyword rules (ordered by specificity) ─────

class IntentRule:
    """A single intent classification rule."""

    def __init__(
        self,
        intent: IntentType,
        patterns: List[str],
        required_all: Optional[List[str]] = None,
        min_match: int = 1,
    ) -> None:
        self.intent = intent
        self.patterns = [p.lower() for p in patterns]
        self.required_all = [r.lower() for r in required_all] if required_all else []
        self.min_match = min_match

    def match(self, query: str) -> bool:
        q = query.lower()
        matches = sum(1 for p in self.patterns if p in q)
        if matches < self.min_match:
            return False
        if self.required_all:
            return all(r in q for r in self.required_all)
        return True


# ── Rule set (ordered: most specific first) ────

_RULES: List[IntentRule] = [
    # Error codes — hex patterns or "DTC" / "P0xxx"
    IntentRule(IntentType.ERROR_CODE, ["dtc", "error code", "trouble code", "fault code"], min_match=1),
    IntentRule(IntentType.ERROR_CODE, ["p0", "p1", "p2", "u0", "u1", "c0", "b0"], min_match=1),
    # CAN signal analysis
    IntentRule(IntentType.CAN_SIGNAL, ["can signal", "can bus", "can message", "signal value",
                                        "raw value", "hex data", "0x"], min_match=1),
    IntentRule(IntentType.CAN_SIGNAL, ["signal", "message id", "arbitration"], min_match=2),
    # Component diagnostics
    IntentRule(IntentType.COMPONENT, ["diagnos", "component", "ecu", "sensor", "actuator",
                                       "module", "valve", "motor", "pump"], min_match=1),
    IntentRule(IntentType.COMPONENT, ["not working", "failure", "fault", "malfunction",
                                       "broken", "no response"], min_match=1),
    IntentRule(IntentType.COMPONENT, ["test", "measure", "check"], required_all=["component"]),
    # Connector lookup
    IntentRule(IntentType.CONNECTOR, ["connector", "pinout", "pin", "terminal",
                                       "harness", "wiring"], min_match=1),
    IntentRule(IntentType.CONNECTOR, ["pin", "wire", "circuit"], required_all=["connector"]),
    # Procedure request
    IntentRule(IntentType.PROCEDURE, ["procedure", "step", "how to", "instruction",
                                       "guide", "replace", "remove", "install"], min_match=1),
    IntentRule(IntentType.PROCEDURE, ["procedure", "steps"], required_all=["procedure"]),
    IntentRule(IntentType.PROCEDURE, ["how to", "how do i", "how can i"], min_match=1),
    # Maintenance
    IntentRule(IntentType.MAINTENANCE, ["maintenance", "service", "inspect", "routine",
                                         "check", "replace", "fluid", "filter",
                                         "lubricat", "torque"], min_match=1),
    IntentRule(IntentType.MAINTENANCE, ["schedule", "interval", "preventive"], min_match=1),
    # Specification
    IntentRule(IntentType.SPECIFICATION, ["specification", "spec", "parameter", "rating",
                                           "capacity", "limit", "range", "value",
                                           "voltage", "current", "resistance", "pressure"], min_match=1),
    IntentRule(IntentType.SPECIFICATION, ["what is the", "specification for", "specs",
                                           "technical data"], min_match=1),
    # Comparison
    IntentRule(IntentType.COMPARISON, ["difference", "compare", "versus", "vs", "or"],
               required_all=["difference"]),
    IntentRule(IntentType.COMPARISON, ["which is better", "which one", "difference between"], min_match=1),
]


class IntentClassifier:
    """Classifies a technician's query into a diagnostic intent.

    Pure pattern-matching — no LLM calls.  Returns ``IntentType.GENERAL``
    when no specific intent matches.
    """

    def classify(self, query: str) -> Tuple[IntentType, List[str]]:
        """Detect the intent behind *query*.

        Parameters
        ----------
        query : str
            The technician's natural-language query.

        Returns
        -------
        (IntentType, matched_phrases)
            The detected intent and the list of matched keyword phrases.
        """
        if not query or not query.strip():
            return IntentType.GENERAL, []

        matched_phrases: List[str] = []
        for rule in _RULES:
            if rule.match(query):
                matched = [p for p in rule.patterns if p in query.lower()]
                matched_phrases.extend(matched)
                return rule.intent, matched_phrases

        return IntentType.GENERAL, []

    def classify_with_confidence(self, query: str) -> Tuple[IntentType, float, List[str]]:
        """Like ``classify`` but also returns a confidence score."""
        intent, phrases = self.classify(query)
        if intent == IntentType.GENERAL and not phrases:
            return intent, 0.0, phrases
        # Simple heuristic: more matched patterns → higher confidence
        confidence = min(0.5 + len(phrases) * 0.15, 0.95)
        return intent, confidence, phrases


def get_template_for_intent(intent: IntentType, template_map: dict) -> str:
    """Resolve the Jinja2 template filename for a given intent.

    Parameters
    ----------
    intent : IntentType
        The detected intent.
    template_map : dict
        Mapping from intent value → template filename.

    Returns
    -------
    str
        Template filename.
    """
    return template_map.get(intent.value, template_map.get("general", "general.jinja"))
