"""LLM adapter implementations.

All adapters expose a common interface defined by BaseLLMAdapter.
The orchestration engine communicates only through BaseLLMAdapter.
"""

from reasoning.adapters.base_adapter import BaseLLMAdapter, LLMResponse, ModelInfo
from reasoning.adapters.ollama_adapter import OllamaAdapter
from reasoning.adapters.openai_adapter import OpenAICompatibleAdapter
from reasoning.adapters.vllm_adapter import VLLMAdapter

__all__ = [
    "BaseLLMAdapter",
    "LLMResponse",
    "ModelInfo",
    "OllamaAdapter",
    "OpenAICompatibleAdapter",
    "VLLMAdapter",
]
