"""Token Estimator — model-aware token counting with graceful fallback.

Tries model-specific tokenizers (tiktoken, HuggingFace) when available
and falls back to a character-based heuristic for unknown models.
"""

from typing import Any, Dict, Optional


class TokenEstimator:
    """Estimates token counts for text using model-aware tokenizers
    when possible.

    Parameters
    ----------
    model_name : str
        Model name used to select the best tokenizer strategy.
    """

    def __init__(self, model_name: str = "") -> None:
        self._model_name = model_name
        self._encoder: Optional[Any] = None
        self._fallback_ratio: float = 4.0  # chars per token
        self._load_tokenizer()

    def estimate(self, text: str) -> int:
        """Return the estimated token count for *text*.

        Uses a model-aware tokenizer when available, otherwise falls
        back to ``len(text) / chars_per_token``.
        """
        if not text:
            return 0
        if self._encoder is not None:
            try:
                return len(self._encoder.encode(text))
            except Exception:
                pass
        return max(1, round(len(text) / self._fallback_ratio))

    def estimate_batch(self, texts: list) -> int:
        """Return the total estimated tokens for a list of texts."""
        return sum(self.estimate(t) for t in texts)

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def fallback_ratio(self) -> float:
        return self._fallback_ratio

    # ── Tokenizer loading ───────────────────────

    def _load_tokenizer(self) -> None:
        mn = self._model_name.lower()

        # Try tiktoken for OpenAI / Ollama models
        if any(k in mn for k in ("gpt", "text-embedding", "qwen", "llama", "mistral", "mixtral", "codestral")):
            enc = self._try_tiktoken()
            if enc:
                self._encoder = enc
                return

        # Try HuggingFace transformers
        for prefix in ("qwen", "llama", "mistral", "mixtral", "gemma", "falcon", "phi", "deepseek"):
            if mn.startswith(prefix):
                enc = self._try_hf_tokenizer()
                if enc:
                    self._encoder = enc
                    return

    @staticmethod
    def _try_tiktoken() -> Optional[Any]:
        try:
            import tiktoken
            try:
                return tiktoken.get_encoding("cl100k_base")
            except Exception:
                try:
                    return tiktoken.encoding_for_model("gpt-4")
                except Exception:
                    return tiktoken.get_encoding("o200k_base")
        except ImportError:
            return None

    @staticmethod
    def _try_hf_tokenizer() -> Optional[Any]:
        try:
            from transformers import AutoTokenizer
            try:
                return AutoTokenizer.from_pretrained("gpt2")
            except Exception:
                return None
        except ImportError:
            return None
