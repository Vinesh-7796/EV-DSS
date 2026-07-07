"""OpenAI-compatible adapter for cloud or self-hosted endpoints.

Supports any OpenAI-compatible chat completion API (OpenAI, Together,
Groq, etc.).  Uses the ``/v1/chat/completions`` endpoint.
"""

import json
import time
from typing import Any, Dict, Generator, Optional

import httpx

from backend.logger import logger
from reasoning.adapters.base_adapter import BaseLLMAdapter, LLMResponse, ModelInfo


class OpenAICompatibleAdapter(BaseLLMAdapter):
    """Adapter for any OpenAI-compatible chat API.

    Parameters
    ----------
    model : str
        Model name (e.g. ``"gpt-4o-mini"``).
    url : str
        Base URL for the API (e.g. ``"https://api.openai.com/v1"``).
    api_key : str
        API key for authentication.
    temperature : float
        Sampling temperature.
    top_p : float
        Nucleus sampling.
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
        top_p: float = 0.9,
        max_tokens: int = 2048,
        context_window: int = 8192,
        timeout_s: int = 120,
    ) -> None:
        self._model = model
        self._url = url.rstrip("/")
        self._api_key = api_key
        self._temperature = temperature
        self._top_p = top_p
        self._max_tokens = max_tokens
        self._context_window = context_window
        self._timeout_s = timeout_s
        self._client: Optional[httpx.Client] = None

    # ── BaseLLMAdapter interface ────────────────

    def generate(self, prompt: str, **kwargs: Any) -> LLMResponse:
        start = time.time()
        endpoint = f"{self._url}/chat/completions"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }

        payload: Dict[str, Any] = {
            "model": kwargs.get("model", self._model),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": kwargs.get("temperature", self._temperature),
            "top_p": kwargs.get("top_p", self._top_p),
            "max_tokens": kwargs.get("max_tokens", self._max_tokens),
        }

        # Enable OpenAI JSON mode when requested
        if kwargs.get("json_mode", False):
            payload["response_format"] = {"type": "json_object"}

        try:
            client = self._get_client()
            response = client.post(endpoint, json=payload, headers=headers, timeout=self._timeout_s)
            response.raise_for_status()
            data = response.json()

            choice = data.get("choices", [{}])[0]
            content = choice.get("message", {}).get("content", "")
            elapsed_ms = (time.time() - start) * 1000.0

            usage = data.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)

            return LLMResponse(
                text=content.strip(),
                success=True,
                model_used=data.get("model", self._model),
                runtime_used="openai",
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                generation_time_ms=round(elapsed_ms, 1),
                raw=data,
            )

        except httpx.ConnectError as exc:
            return LLMResponse(
                success=False,
                error=f"OpenAI endpoint unreachable: {exc}",
                model_used=self._model,
                runtime_used="openai",
                generation_time_ms=(time.time() - start) * 1000.0,
            )
        except httpx.HTTPStatusError as exc:
            return LLMResponse(
                success=False,
                error=f"OpenAI HTTP {exc.response.status_code}: {exc.response.text[:200]}",
                model_used=self._model,
                runtime_used="openai",
                generation_time_ms=(time.time() - start) * 1000.0,
            )
        except Exception as exc:
            return LLMResponse(
                success=False,
                error=f"OpenAI error: {exc}",
                model_used=self._model,
                runtime_used="openai",
                generation_time_ms=(time.time() - start) * 1000.0,
            )

    def stream_generate(self, prompt: str, **kwargs: Any) -> Generator[str, None, None]:
        """Yield content chunks via OpenAI streaming (SSE)."""
        endpoint = f"{self._url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }

        payload: Dict[str, Any] = {
            "model": kwargs.get("model", self._model),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": kwargs.get("temperature", self._temperature),
            "max_tokens": kwargs.get("max_tokens", self._max_tokens),
            "stream": True,
        }

        if kwargs.get("json_mode", False):
            payload["response_format"] = {"type": "json_object"}

        client = self._get_client()
        try:
            with client.stream("POST", endpoint, json=payload, headers=headers, timeout=self._timeout_s) as resp:
                for line in resp.iter_lines():
                    if not line or line.startswith(":") or line.startswith("data: [DONE]"):
                        continue
                    if line.startswith("data: "):
                        try:
                            chunk = json.loads(line[6:])
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue
        except Exception as exc:
            yield f"[Stream error: {exc}]"

    def health_check(self) -> ModelInfo:
        endpoint = f"{self._url}/models"
        headers = {"Authorization": f"Bearer {self._api_key}"}
        try:
            client = self._get_client()
            resp = client.get(endpoint, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            models = {m.get("id", "") for m in data.get("data", [])}
            if self._model in models:
                return ModelInfo(
                    name=self._model,
                    runtime="openai",
                    context_window=self._context_window,
                    supports_streaming=True,
                    supports_json_mode=True,
                    healthy=True,
                )
            return ModelInfo(
                name=self._model,
                runtime="openai",
                healthy=False,
                error=f"Model '{self._model}' not found. Available: {', '.join(sorted(models))[:200]}",
            )
        except httpx.ConnectError as exc:
            return ModelInfo(name=self._model, runtime="openai", healthy=False, error=str(exc))
        except Exception as exc:
            return ModelInfo(name=self._model, runtime="openai", healthy=False, error=str(exc))

    def model_info(self) -> ModelInfo:
        return self.health_check()

    @property
    def supports_json_mode(self) -> bool:
        return True

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(timeout=self._timeout_s)
        return self._client



