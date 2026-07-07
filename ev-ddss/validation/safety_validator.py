"""SAFETY VALIDATION — enforces EV diagnostic safety rules.

Profiling instrumentation added.
"""

import time
from typing import Any, List

from backend.logger import logger


class SafetyValidationResults:
    """Results of safety validation."""

    def __init__(
        self,
        triggered_rules: List[str] = None,
        is_safe: bool = True,
        missing_warnings: List[str] = None,
    ) -> None:
        self.triggered_rules = triggered_rules or []
        self.is_safe = is_safe
        self.missing_warnings = missing_warnings or []


class SafetyValidator:
    """Enforces automotive safety rules for EV diagnostics."""

    def __init__(self, config: Any = None) -> None:
        self.config = config or {}
        self.active_rules = list(getattr(self.config, "safety_rule_sets", [])) if not isinstance(self.config, dict) else list(self.config.get("safety_rule_sets", []))

    def validate(self, diagnostic_response: Any) -> Any:
        """Validate the diagnostic response against safety rules.

        Parameters
        ----------
        diagnostic_response : Any
            The LLM-generated diagnostic response to validate.

        Returns
        -------
        SafetyValidationResults
            Safety validation results.
        """
        start = time.time()
        logger.info("SafetyValidator: starting validation")

        # Simulate safety validation with profiling
        results = self._validate_safety(diagnostic_response)
        elapsed_ms = (time.time() - start) * 1000
        logger.info("SafetyValidator: completed in %.3f ms, safe=%s",
                     elapsed_ms, results.is_safe)

        return results

    def _validate_safety(self, diagnostic_response: Any) -> Any:
        """Internal safety validation logic."""

        # Create results object
        results = SafetyValidationResults()

        # Simulate safety checks based on diagnostic content
        # In production, this would enforce actual EV safety rules

        # Example safety rules (simulated)
        safety_rules = [
            "Check for live voltage before opening panels",
            "Ensure proper grounding before testing",
            "Verify coolant is neutralized",
            "Check battery management system status",
            "Verify charger is unplugged before repairs"
        ]

        # Check for high-voltage / EV safety-relevant content first. Ordinary
        # low-voltage UX diagnostics should not fail safety validation merely
        # because a generic word like "system" appears.
        response_text = str(diagnostic_response).lower()
        safety_relevant_keywords = [
            "high voltage", "hv", "battery", "pack", "inverter", "contactor",
            "charger", "isolation", "coolant", "traction", "dc bus",
        ]
        if not any(keyword in response_text for keyword in safety_relevant_keywords):
            return results

        triggered = []

        for rule in safety_rules:
            rule_keywords = [word for word in rule.lower().split() if len(word) > 3]
            has_warning = all(keyword in response_text for keyword in rule_keywords[:2])
            if not has_warning:
                triggered.append(rule)

        # Update results
        results.triggered_rules = triggered
        results.is_safe = len(triggered) == 0

        # Provide safety warnings for triggered rules
        for rule in triggered:
            results.missing_warnings.append(f"Safety rule triggered: {rule}")

        return results
