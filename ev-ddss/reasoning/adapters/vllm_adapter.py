"""vLLM adapter — placeholder for future self-hosted vLLM deployment.

Provides the same ``BaseLLMAdapter`` interface.  Stub implementation
that returns controlled errors until configured.
"""

from typing import Any

from backend.logger import logger
from reasoning.adapters.base_adapter import BaseLLMAdapter, LLMResponse, ModelInfo


class VLLMAdapter(BaseLLMAdapter):
    """Adapter for vLLM (uses OpenAI-compatible API under the hood).

    Parameters
    ----------
    model : str
        vLLM model name.
    url : str
        vLLM server URL (e.g. ``http://localhost:8000/v1``).
    api_key : str
        Optional API key.
    temperature : float
        Sampling temperature.
    max_tokens : int
        Maximum tokens in the completion.
    context_window : int
        Model context window.
    timeout_s : int
        HTTP request timeout.
    """

    def __init__(
        self,
        model: str = "",
        url: str = "",
        api_key: str = "",
        temperature: float = 0.1,
        max_tokens: int = 2048,
        context_window: int = 8192,
        timeout_s: int = 120,
    ) -> None:
        self._model = model
        self._url = url
        self._api_key = api_key
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._context_window = context_window
        self._timeout_s = timeout_s

    def generate(self, prompt: str, **kwargs: Any) -> LLMResponse:
        return LLMResponse(
            success=False,
            error="vLLM adapter is a placeholder. Configure 'runtime: openai' "
                  "to use vLLM via its OpenAI-compatible endpoint.",
            model_used=self._model,
            runtime_used="vllm",
        )

    def health_check(self) -> ModelInfo:
        return ModelInfo(
            name=self._model or "(not configured)",
            runtime="vllm",
            healthy=False,
            error="vLLM adapter is not yet implemented.",
        )

    def model_info(self) -> ModelInfo:
        return self.health_check()

    @property
    def supports_json_mode(self) -> bool:
        return False
