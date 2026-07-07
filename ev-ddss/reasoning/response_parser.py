"""Response Parser — validates and parses the LLM's JSON output into
a ``DiagnosticResponse``.

Supports
────────

* JSON syntax validation
* Required field presence checks
* Schema compliance via Pydantic
* Automatic recovery for common JSON formatting errors
* Controlled error responses when recovery fails
"""

import json
import re
from typing import Any, Dict, Optional

from backend.logger import logger
from reasoning.models.diagnostic_response import DiagnosticResponse


class ParseResult:
    """Outcome of parsing an LLM response."""

    def __init__(
        self,
        response: Optional[DiagnosticResponse] = None,
        success: bool = False,
        error: str = "",
        recovery_used: bool = False,
        raw_text: str = "",
    ) -> None:
        self.response = response
        self.success = success
        self.error = error
        self.recovery_used = recovery_used
        self.raw_text = raw_text

    def __bool__(self) -> bool:
        return self.success and self.response is not None


class ResponseParser:
    """Parses and validates JSON responses from the LLM.

    Parameters
    ----------
    strict : bool
        If True, reject responses with missing optional fields.
        If False, fill missing optionals with defaults.
    max_recovery_attempts : int
        Number of recovery strategies to try before giving up.
    """

    _REQUIRED_FIELDS = [
        "problem_summary",
        "possible_causes",
        "inspection_steps",
        "recommended_actions",
    ]

    def __init__(self, strict: bool = True, max_recovery_attempts: int = 3) -> None:
        self._strict = strict
        self._max_recovery_attempts = max_recovery_attempts

    def parse(self, raw_text: str) -> ParseResult:
        """Parse and validate an LLM response.

        Parameters
        ----------
        raw_text : str
            Raw text output from the LLM.

        Returns
        -------
        ParseResult
            Success status, parsed DiagnosticResponse (or None), error message.
        """
        if not raw_text or not raw_text.strip():
            return ParseResult(success=False, error="Empty response from LLM.", raw_text=raw_text)

        # Attempt 1: Direct JSON parse
        data, error = self._try_parse_json(raw_text)
        if data is not None:
            return self._validate(data, recovery_used=False, raw_text=raw_text)

        # Attempt 2: Recovery strategies
        recovered_data = self._attempt_recovery(raw_text)
        if recovered_data is not None:
            logger.info("ResponseParser: recovered malformed JSON")
            return self._validate(recovered_data, recovery_used=True, raw_text=raw_text)

        return ParseResult(
            success=False,
            error=f"Failed to parse LLM response. {error}",
            raw_text=raw_text,
        )

    # ── JSON extraction ─────────────────────────

    @staticmethod
    def _try_parse_json(text: str) -> tuple:
        """Attempt to parse JSON from text, trying multiple extraction strategies."""
        # Strategy 1: Direct parse
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                return data, None
        except json.JSONDecodeError:
            pass

        # Strategy 2: Extract JSON block from markdown
        json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1).strip())
                if isinstance(data, dict):
                    return data, None
            except json.JSONDecodeError:
                pass

        # Strategy 3: Find outermost { ... }
        brace_match = re.search(r"\{.*\}", text, re.DOTALL)
        if brace_match:
            try:
                data = json.loads(brace_match.group(0))
                if isinstance(data, dict):
                    return data, None
            except json.JSONDecodeError:
                pass

        return None, "No valid JSON object found in response."

    # ── Recovery strategies ─────────────────────

    def _attempt_recovery(self, text: str) -> Optional[Dict[str, Any]]:
        """Try to repair common JSON formatting issues."""
        strategies = [
            self._fix_trailing_commas,
            self._fix_single_quotes,
            self._fix_unquoted_keys,
            self._extract_partial_json,
        ]

        for strategy in strategies:
            result = strategy(text)
            if result is not None:
                return result
        return None

    @staticmethod
    def _fix_trailing_commas(text: str) -> Optional[Dict[str, Any]]:
        """Remove trailing commas before closing braces/brackets."""
        # Only try on content that looks like JSON
        if "{" not in text:
            return None
        fixed = re.sub(r",\s*([}\]])", r"\1", text)
        if fixed == text:
            return None
        try:
            return json.loads(fixed)
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _fix_single_quotes(text: str) -> Optional[Dict[str, Any]]:
        """Replace single quotes with double quotes where safe."""
        if "{" not in text:
            return None
        # Replace single quotes around keys and string values
        fixed = re.sub(r"'([^']*)'", r'"\1"', text)
        if fixed == text:
            return None
        try:
            return json.loads(fixed)
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _fix_unquoted_keys(text: str) -> Optional[Dict[str, Any]]:
        """Quote unquoted JSON keys."""
        if "{" not in text:
            return None
        # Match unquoted keys: {key: value} → {"key": value}
        fixed = re.sub(r"([{,])\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:", r'\1"\2":', text)
        if fixed == text:
            return None
        try:
            return json.loads(fixed)
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _extract_partial_json(text: str) -> Optional[Dict[str, Any]]:
        """Try to extract a partial JSON object from truncated output."""
        brace_count = 0
        start = -1
        for i, ch in enumerate(text):
            if ch == "{":
                if start == -1:
                    start = i
                brace_count += 1
            elif ch == "}":
                brace_count -= 1
                if brace_count == 0 and start != -1:
                    segment = text[start:i + 1]
                    try:
                        return json.loads(segment)
                    except json.JSONDecodeError:
                        pass
        # Truncated: close unclosed braces
        if start != -1 and brace_count > 0:
            segment = text[start:] + "}" * brace_count
            try:
                return json.loads(segment)
            except json.JSONDecodeError:
                pass
        return None

    # ── Validation ──────────────────────────────

    def _validate(self, data: Dict[str, Any], recovery_used: bool, raw_text: str) -> ParseResult:
        errors: list = []

        # Check required fields
        for field in self._REQUIRED_FIELDS:
            if field not in data or data[field] is None:
                errors.append(f"Missing required field: '{field}'")
            elif isinstance(data[field], (list, str)) and len(data[field]) == 0:
                errors.append(f"Field '{field}' is empty")

        # Type checks for list fields
        for field in ["possible_causes", "inspection_steps", "recommended_actions"]:
            if field in data and not isinstance(data[field], list):
                errors.append(f"Field '{field}' must be a list")

        # String field checks
        for field in ["problem_summary", "reasoning_summary"]:
            if field in data and data[field] is not None and not isinstance(data[field], str):
                errors.append(f"Field '{field}' must be a string")

        if errors:
            err_msg = "; ".join(errors)
            logger.warning("ResponseParser: validation failed - {}", err_msg)

            # If strict, fail
            if self._strict:
                return ParseResult(success=False, error=err_msg, recovery_used=recovery_used, raw_text=raw_text)

            # Non-strict: fill missing fields with defaults
            defaults = {
                "possible_causes": ["Unknown cause"],
                "inspection_steps": ["Refer to service manual"],
                "recommended_actions": ["Consult manufacturer documentation"],
                "referenced_entities": [],
                "referenced_documents": [],
                "reasoning_summary": "",
                "citations": [],
                "related_components": [],
                "connectors": [],
                "fuses": [],
                "relays": [],
                "can_signals": [],
                "metadata": {},
            }
            for key, default in defaults.items():
                if key not in data or not data[key]:
                    data[key] = default

        try:
            response = DiagnosticResponse(**data)
            return ParseResult(response=response, success=True, recovery_used=recovery_used, raw_text=raw_text)
        except Exception as exc:
            return ParseResult(success=False, error=f"Schema validation failed: {exc}", raw_text=raw_text)
