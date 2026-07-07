"""Base abstraction for all LLM adapters.

Every adapter implements the same interface so the orchestration engine
never couples to any specific runtime.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ModelInfo:
    """Metadata about the loaded model."""

    name: str = ""
    runtime: str = ""
    context_window: int = 0
    supports_streaming: bool = False
    supports_json_mode: bool = False
    healthy: bool = False
    error: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMResponse:
    """Normalised response from any LLM adapter."""

    text: str = ""
    success: bool = False
    error: str = ""
    model_used: str = ""
    runtime_used: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    generation_time_ms: float = 0.0
    raw: Any = None


class BaseLLMAdapter(ABC):
    """Abstract adapter for LLM inference.

    The orchestration engine communicates exclusively through this
    interface.  To add a new runtime (vLLM, Anthropic, etc.),
    subclass this and implement all abstract methods.
    """

    @abstractmethod
    def generate(self, prompt: str, **kwargs: Any) -> LLMResponse:
        """Send a prompt to the LLM and return the response.

        Parameters
        ----------
        prompt : str
            The full prompt text to send.
        **kwargs
            Runtime-specific overrides (temperature, max_tokens, json_mode, etc.).

        Returns
        -------
        LLMResponse
            Normalised response with text, tokens, timing.
        """
        ...

    @abstractmethod
    def health_check(self) -> ModelInfo:
        """Check whether the runtime and model are available.

        Returns
        -------
        ModelInfo
            Health status with error message if unavailable.
        """
        ...

    @abstractmethod
    def model_info(self) -> ModelInfo:
        """Return metadata about the currently configured model.

        Returns
        -------
        ModelInfo
            Model name, context window, streaming support, JSON mode support.
        """
        ...

    def stream_generate(self, prompt: str, **kwargs: Any) -> Any:
        """Streaming generation — yields response chunks.

        Default implementation raises NotImplementedError.
        Override in adapters that support streaming.
        """
        raise NotImplementedError("Streaming is not implemented for this adapter.")

    @property
    def supports_json_mode(self) -> bool:
        """Whether this adapter supports native structured output / JSON mode."""
        return False
