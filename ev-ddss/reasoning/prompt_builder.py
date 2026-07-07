"""Prompt Builder — constructs the final LLM prompt from components.

Pipeline
────────

    System Instructions
    ↓
    Engineering Rules
    ↓
    JSON Mode Instruction (optional)
    ↓
    Conversation History (optional)
    ↓
    Prompt Template
    ↓
    Retrieved Context
    ↓
    Technician Query

Construction is entirely template-driven.  No hardcoded prompt logic.
"""

from typing import Any, Dict, List, Optional

from backend.logger import logger
from reasoning.template_manager import TemplateManager


class PromptBuilder:
    """Assembles the final LLM prompt from pluggable components.

    Parameters
    ----------
    template_manager : TemplateManager
        Loaded template manager instance.
    system_prompt : str
        Base system instructions.
    engineering_rules : str or None
        Optional engineering domain rules appended to system prompt.
    json_mode_instruction : str or None
        Instruction injected when JSON mode is active.
    """

    def __init__(
        self,
        template_manager: TemplateManager,
        system_prompt: str = "You are an automotive diagnostic engineering decision support system. Use ONLY the supplied engineering context to answer.",
        engineering_rules: Optional[str] = None,
        json_mode_instruction: Optional[str] = None,
    ) -> None:
        self._template_manager = template_manager
        self._system_prompt = system_prompt
        self._engineering_rules = engineering_rules or (
            "You are an automotive diagnostic assistant. "
            "You MUST answer using ONLY the supplied engineering context below. "
            "NEVER use your pretrained knowledge to answer engineering questions. "
            "If the retrieved context does not contain sufficient information, "
            "state clearly that no supporting engineering evidence was found. "
            "Do not fabricate specifications, error codes, or procedures. "
            "Cite every claim using the citation strings provided. "
            "When referencing data from a table, include the table name and row."
        )
        self._json_mode_instruction = json_mode_instruction or (
            "You MUST respond with valid JSON ONLY. "
            "Do NOT include markdown formatting, explanations, or any text "
            "outside the JSON structure. Output a single JSON object."
        )

    # ── Public API ──────────────────────────────

    def build(
        self,
        template_name: str,
        context_text: str,
        query: str,
        intent: str = "",
        conversation_history: Optional[List[Dict[str, str]]] = None,
        extra_variables: Optional[Dict[str, Any]] = None,
        json_mode: bool = False,
    ) -> str:
        """Construct the complete prompt for LLM inference.

        Parameters
        ----------
        template_name : str
            Jinja2 template filename.
        context_text : str
            Optimised context text (already rendered / joined).
        query : str
            The technician's original query.
        intent : str
            Detected intent label.
        conversation_history : list of dict or None
            Past turn(s) as ``[{"role": "...", "content": "..."}]``.
        extra_variables : dict or None
            Additional template variables.
        json_mode : bool
            Whether to inject strict JSON-only instruction.

        Returns
        -------
        str
            Fully assembled prompt string.
        """
        history_text = ""
        if conversation_history:
            history_lines = []
            for turn in conversation_history[-10:]:
                role = turn.get("role", "unknown")
                content = turn.get("content", "")
                history_lines.append(f"[{role}]: {content}")
            history_text = "\n".join(history_lines)

        variables: Dict[str, Any] = {
            "system_prompt": self._system_prompt,
            "engineering_rules": self._engineering_rules,
            "json_mode_instruction": self._json_mode_instruction if json_mode else "",
            "context": context_text,
            "query": query,
            "intent": intent,
            "conversation_history": history_text,
            "diagnostic_response_schema": self._schema_definition(),
        }
        if extra_variables:
            variables.update(extra_variables)

        rendered = self._template_manager.render(template_name, **variables)
        return rendered

    def build_system_message(self, json_mode: bool = False) -> str:
        """Return the system message alone (for chat-based APIs)."""
        parts = [self._system_prompt, self._engineering_rules]
        if json_mode:
            parts.append(self._json_mode_instruction)
        return "\n\n".join(parts)

    @staticmethod
    def _sanitize_text(text: str) -> str:
        if not isinstance(text, str):
            return str(text) if text is not None else ""
        """Remove image file extensions that Ollama may interpret as image references."""
        import re
        # Strip .png, .jpg, .jpeg, .gif, .bmp, .webp when they appear as filename extensions
        text = re.sub(r'\b\w+\.png\b', '[image]', text, flags=re.IGNORECASE)
        text = re.sub(r'\b\w+\.jpg\b', '[image]', text, flags=re.IGNORECASE)
        text = re.sub(r'\b\w+\.jpeg\b', '[image]', text, flags=re.IGNORECASE)
        text = re.sub(r'\b\w+\.gif\b', '[image]', text, flags=re.IGNORECASE)
        text = re.sub(r'\b\w+\.bmp\b', '[image]', text, flags=re.IGNORECASE)
        text = re.sub(r'\b\w+\.webp\b', '[image]', text, flags=re.IGNORECASE)
        # Also replace bare image format abbreviations in parentheses (e.g. "(2960x3907, PNG)")
        text = re.sub(r'\(\d+x\d+,\s*\w+\)', '(image)', text)
        return text

    @staticmethod
    def build_context_text(
        semantic_context: List[Any],
        exact_matches: List[Any],
        graph_context: List[Any],
        image_references: List[Any],
    ) -> str:
        """Flatten retrieval results into a single formatted context string.

        This is called *after* the ``ContextOptimizer`` has trimmed and
        ranked the results.
        """
        parts: List[str] = []

        if semantic_context:
            parts.append("=== SEMANTIC CONTEXT (ranked by relevance) ===")
            for r in semantic_context:
                score = getattr(r, "score", 0)
                content = PromptBuilder._sanitize_text(getattr(r, "content", ""))
                source = PromptBuilder._sanitize_text(getattr(r, "source", ""))
                parts.append(f"[score={score:.3f}] [{source}] {content}")

        if exact_matches:
            parts.append("\n=== EXACT MATCHES ===")
            for r in exact_matches:
                content = PromptBuilder._sanitize_text(getattr(r, "content", ""))
                source = PromptBuilder._sanitize_text(getattr(r, "source", ""))
                parts.append(f"[{source}] {content}")

        if graph_context:
            parts.append("\n=== GRAPH CONTEXT (entity relationships) ===")
            for r in graph_context:
                content = PromptBuilder._sanitize_text(getattr(r, "content", ""))
                parts.append(f"  {content}")

        if image_references:
            parts.append("\n=== IMAGE REFERENCES (OCR text) ===")
            for r in image_references:
                content = PromptBuilder._sanitize_text(getattr(r, "content", ""))
                source = PromptBuilder._sanitize_text(getattr(r, "source", ""))
                parts.append(f"[{source}] {content}")

        if not parts:
            parts.append("(No relevant context found.)")

        return "\n".join(parts)

    @staticmethod
    def _schema_definition() -> str:
        return """{
  "problem_summary": "string — concise problem description",
  "possible_causes": ["string — ordered list, most likely first"],
  "inspection_steps": ["string — step-by-step test procedures"],
  "recommended_actions": ["string — repair or corrective actions"],
  "referenced_entities": ["string — IDs of referenced error codes, ECUs, etc."],
  "referenced_documents": ["string — source documents used"],
  "reasoning_summary": "string — brief reasoning explanation",
  "citations": ["string — citation strings for each claim"],
  "related_components": ["string — component names related to this fault (e.g. inverter, motor, BMS)"],
  "connectors": ["string — connector IDs involved (e.g. C21, C101)"],
  "fuses": ["string — fuse IDs involved (e.g. F2, F10A)"],
  "relays": ["string — relay IDs involved (e.g. R1, main contactor)"],
  "can_signals": ["string — CAN bus signal IDs (e.g. 0x521, VCU_TORQUE_CMD)"]
}"""
