"""CONSISTENCY CHECKER — validates internal consistency of diagnostic response.

Profiling instrumentation added.
"""

import time
from typing import Any

from backend.logger import logger


class ConsistencyValidationResults:
    """Results of consistency checking."""

    def __init__(self, issues: Any = None, is_consistent: bool = True) -> None:
        self.issues: Any = issues or []
        self.is_consistent = is_consistent
        self.inconsistent_entities: Any = []
        self.contradictions: Any = []


class ConsistencyChecker:
    """Validates internal consistency of diagnostic response claims."""

    def __init__(self) -> None:
        pass

    def validate(self, diagnostic_response: Any) -> Any:
        """Check for internal consistency in the diagnostic response.

        Parameters
        ----------
        diagnostic_response : Any
            The LLM-generated diagnostic response to check.

        Returns
        -------
        ConsistencyValidationResults
            Consistency check results.
        """
        start = time.time()
        logger.info("ConsistencyChecker: starting validation")

        # Simulate consistency validation with profiling
        results = self._validate_consistency(diagnostic_response)
        elapsed_ms = (time.time() - start) * 1000
        logger.info("ConsistencyChecker: completed in %.3f ms, issues=%d, consistent=%s",
                     elapsed_ms, len(results.issues), results.is_consistent)

        return results

    def _validate_consistency(self, diagnostic_response: Any) -> Any:
        """Internal consistency validation logic."""

        # Create results object
        class SimpleResults:
            def __init__(self):
                self.issues = []
                self.is_consistent = True
                self.inconsistent_entities = []
                self.contradictions = []

        results = SimpleResults()

        # Simulate consistency checks
        # In production, this would check for logical contradictions,
        # format issues, and temporal inconsistencies

        # Example consistency checks (simulated)
        checks = self._get_consistency_checks()

        for check in checks:
            is_valid = self._perform_consistency_check(check, diagnostic_response)

            if not is_valid:
                issue = {
                    "issue": check["name"],
                    "description": check["description"],
                    "severity": check["severity"]
                }
                results.issues.append(issue)
                if check["name"] == "reference_consistency":
                    results.inconsistent_entities.append(issue)
                if check["name"] == "claim_format":
                    results.contradictions.append(issue)

        inconsistent_entities = self._find_inconsistent_entities(diagnostic_response)
        if inconsistent_entities:
            results.inconsistent_entities.extend(inconsistent_entities)
            results.issues.extend(inconsistent_entities)

        contradictions = self._find_contradictions(diagnostic_response)
        if contradictions:
            results.contradictions.extend(contradictions)
            results.issues.extend(contradictions)

        # Update consistency status
        results.is_consistent = len(results.issues) == 0

        return results

    def _find_inconsistent_entities(self, diagnostic_response: Any) -> list:
        entities = getattr(diagnostic_response, "entities", {}) or {}
        issues = []
        for entity_type, values in entities.items():
            normalized = {}
            for value in values or []:
                key = "".join(ch for ch in str(value).lower() if ch.isalnum())
                if key in normalized and normalized[key] != value:
                    issues.append({
                        "issue": "inconsistent_entity_name",
                        "description": f"{entity_type} contains inconsistent spellings: {normalized[key]} / {value}",
                        "severity": "MEDIUM",
                    })
                else:
                    normalized[key] = value
        return issues

    def _find_contradictions(self, diagnostic_response: Any) -> list:
        summary = str(getattr(diagnostic_response, "problem_summary", "")).lower()
        causes = " ".join(getattr(diagnostic_response, "possible_causes", []) or []).lower()
        if "good" in summary and any(word in causes for word in ("fault", "failure", "major")):
            return [{
                "issue": "contradictory_statement",
                "description": "Problem summary says system is good while causes mention a fault",
                "severity": "HIGH",
            }]
        return []

    def _get_consistency_checks(self) -> list:
        """Get list of consistency checks to perform."""

        return [
            {
                "name": "claim_format",
                "description": "All claims should be properly formatted strings",
                "severity": "MEDIUM"
            },
            {
                "name": "reference_consistency",
                "description": "All referenced entities should exist",
                "severity": "HIGH"
            },
            {
                "name": "action_order",
                "description": "Recommended actions should be in logical order",
                "severity": "MEDIUM"
            },
            {
                "name": "component_relationships",
                "description": "Related components should have valid relationships",
                "severity": "HIGH"
            },
            {
                "name": "safety_compliance",
                "description": "Response should not contain unsafe recommendations",
                "severity": "CRITICAL"
            }
        ]

    def _perform_consistency_check(self, check: dict, diagnostic_response: Any) -> bool:
        """Perform a specific consistency check."""

        check_name = check["name"]

        # Simulate check logic
        if check_name == "claim_format":
            return self._check_claim_format(diagnostic_response)
        elif check_name == "reference_consistency":
            return self._check_reference_consistency(diagnostic_response)
        elif check_name == "action_order":
            return self._check_action_order(diagnostic_response)
        elif check_name == "component_relationships":
            return self._check_component_relationships(diagnostic_response)
        elif check_name == "safety_compliance":
            return self._check_safety_compliance(diagnostic_response)
        else:
            return True  # Default to passing unknown checks

    def _check_claim_format(self, diagnostic_response: Any) -> bool:
        """Check if all claims are properly formatted."""

        # Simulate format checking
        fields_to_check = [
            'problem_summary', 'possible_causes', 'inspection_steps',
            'recommended_actions', 'related_components', 'connectors'
        ]

        for field in fields_to_check:
            if hasattr(diagnostic_response, field):
                value = getattr(diagnostic_response, field)
                if isinstance(value, str) and value and len(value.strip()) < 1:
                    return False
                elif isinstance(value, list):
                    for item in value:
                        if not isinstance(item, str) or len(item) < 1:
                            return False

        return True

    def _check_reference_consistency(self, diagnostic_response: Any) -> bool:
        """Check if referenced entities exist."""

        # Simulate reference checking
        # In production, this would validate against knowledge graph

        known_entities = self._get_known_entities()

        all_references = []

        # Add references from various fields
        if hasattr(diagnostic_response, 'related_components'):
            all_references.extend(diagnostic_response.related_components)
        if hasattr(diagnostic_response, 'connectors'):
            all_references.extend(diagnostic_response.connectors)
        if hasattr(diagnostic_response, 'fuses'):
            all_references.extend(diagnostic_response.fuses)
        if hasattr(diagnostic_response, 'relays'):
            all_references.extend(diagnostic_response.relays)
        if hasattr(diagnostic_response, 'can_signals'):
            all_references.extend(diagnostic_response.can_signals)

        for ref in all_references:
            normalized = str(ref).strip().lower().replace(" ", "_")
            if normalized and normalized not in known_entities:
                return False

        return True

    def _check_action_order(self, diagnostic_response: Any) -> bool:
        """Check if actions are in logical order."""

        # Simulate action order checking
        # In production, this would evaluate logical dependencies

        if not hasattr(diagnostic_response, 'recommended_actions'):
            return True

        actions = diagnostic_response.recommended_actions

        # Simple check: ensure actions are ordered by safety/criticality
        # For simulation, assume they are properly ordered
        return True

    def _check_component_relationships(self, diagnostic_response: Any) -> bool:
        """Check if component relationships are valid."""

        # Simulate relationship checking
        # In production, this would validate component relationships

        # For simulation, return True
        return True

    def _check_safety_compliance(self, diagnostic_response: Any) -> bool:
        """Check if response contains unsafe recommendations."""

        # Simulate safety compliance checking
        if not hasattr(diagnostic_response, 'recommended_actions'):
            return True

        actions = diagnostic_response.recommended_actions

        # Check for unsafe action patterns (simulated)
        unsafe_keywords = [
            "bypass safety", "disable protection", "remove guard",
            "override interlock", "short circuit", "dangerous procedure"
        ]

        for action in actions:
            action_lower = action.lower()
            for keyword in unsafe_keywords:
                if keyword in action_lower:
                    return False

        return True

    def _get_known_entities(self) -> set:
        """Get set of known entities from knowledge base."""

        return {
            "motor", "inverter", "bms", "cooling_system",
            "ntc1", "c42", "f21", "k5", "p1", "sensor", "ecu", "ccu",
            "battery", "charger", "contactor", "relays", "fuses",
            "can_signal_0x101", "can_signal_0x182", "can_signal_0x201",
            "traction_system", "power_train", "thermal_management"
        }
