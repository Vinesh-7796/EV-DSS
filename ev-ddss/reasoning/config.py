"""Configuration for the LLM Orchestration Engine.

All runtime, model, and template settings are loaded from the global
application configuration. No hardcoded values in business logic.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from backend.logger import logger
from config import get_settings


@dataclass
class ReasoningConfig:
    """Fully resolved configuration for the reasoning engine.

    Populated from ``config.get_settings().reasoning`` with sensible
    defaults for local development (Ollama + qwen3:8b).
    """

    # ── Runtime ─────────────────────────────────
    runtime: str = "ollama"
    model: str = "qwen3:8b"
    temperature: float = 0.1
    top_p: float = 0.9
    max_tokens: int = 2048
    context_window: int = 8192
    system_prompt: str = "You are an expert automotive diagnostic assistant."
    template_directory: str = ""

    # ── Adapter endpoints ───────────────────────
    ollama_url: str = "http://localhost:11434"
    openai_url: str = ""
    openai_api_key: str = ""
    openai_model: str = ""
    vllm_url: str = ""
    vllm_model: str = ""

    # ── Context optimization ────────────────────
    max_context_tokens: int = 4096
    deduplicate_context: bool = True
    rank_by_score: bool = True

    # ── Intents & templates ─────────────────────
    template_map: Dict[str, str] = field(default_factory=lambda: {
        "error_code": "error_code.jinja",
        "component": "component.jinja",
        "can_signal": "can_signal.jinja",
        "procedure": "procedure.jinja",
        "maintenance": "maintenance.jinja",
        "comparison": "general.jinja",
        "connector": "general.jinja",
        "specification": "general.jinja",
        "general": "general.jinja",
    })

    # ── JSON mode ───────────────────────────────
    json_mode: bool = True
    json_mode_system_instruction: str = (
        "You MUST respond with valid JSON ONLY. "
        "Do NOT include markdown formatting, explanations, or any text "
        "outside the JSON structure. Output a single JSON object."
    )

    # ── Conversation history ────────────────────
    enable_history: bool = False
    max_history_turns: int = 5

    # ── Streaming ───────────────────────────────
    enable_streaming: bool = False

    # ── Token estimation ────────────────────────
    token_estimator: str = "auto"
    token_estimator_fallback_ratio: float = 4.0

    # ── Template versioning ─────────────────────
    template_version: str = "1.0.0"

    # ── Behaviour flags ─────────────────────────
    strict_validation: bool = True
    retry_on_parse_failure: bool = True
    max_retries: int = 2
    request_timeout_s: int = 300

    # ── Derived paths (set during resolve) ──────
    resolved_template_dir: Path = field(default_factory=lambda: Path("reasoning/templates"))

    def resolve(self) -> "ReasoningConfig":
        """Load settings from global config and resolve derived values."""
        settings = get_settings()

        if not self.model:
            self.model = settings.llm.model or self.model
        if self.temperature == 0.1:
            self.temperature = settings.llm.temperature
        if self.max_tokens == 2048:
            self.max_tokens = settings.llm.max_tokens
        if self.context_window == 8192:
            self.context_window = settings.llm.context_length

        r = getattr(settings, "reasoning", None)
        if r is not None:
            for key in self.__dict__:
                if hasattr(r, key) and key not in ("resolved_template_dir",):
                    rval = getattr(r, key)
                    current = getattr(self, key)
                    if rval is not None and rval != "" and current == ReasoningConfig().__dict__.get(key):
                        setattr(self, key, rval)

        if self.template_directory:
            self.resolved_template_dir = Path(self.template_directory)
        else:
            from pathlib import Path as P
            self.resolved_template_dir = P(__file__).resolve().parent / "templates"

        logger.debug("ReasoningConfig resolved: runtime={} model={} templates={}",
                      self.runtime, self.model, self.resolved_template_dir)
        return self

    @classmethod
    def from_settings(cls) -> "ReasoningConfig":
        return cls().resolve()

    def timeline(self) -> Dict:
        return {
            "runtime": self.runtime,
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "context_window": self.context_window,
        }
