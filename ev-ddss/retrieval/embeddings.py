"""Embedding Generation — produces vector embeddings for text chunks
using a local sentence-transformer model.

Supports configurable models, batched inference, and optional on-disk
caching of computed embeddings to avoid recomputation.
"""

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.logger import logger
from config import get_settings

# ──────────────────────────────────────────────
#  Lazy import for sentence-transformers
# ──────────────────────────────────────────────

_HAS_SENTENCE_TRANSFORMERS = False
try:
    from sentence_transformers import SentenceTransformer

    _HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    SentenceTransformer = None  # type: ignore[assignment]


# ──────────────────────────────────────────────
#  EmbeddingGenerator
# ──────────────────────────────────────────────


class EmbeddingGenerator:
    """Generates vector embeddings for text content.

    Uses ``sentence-transformers`` when available; falls back to a
    deterministic random seed for development / testing.

    Parameters
    ----------
    model_name : str
        Name of the sentence-transformers model (default from config).
    device : str
        Inference device — ``"cpu"`` or ``"cuda"`` (default from config).
    cache_dir : str or Path
        Directory for caching embeddings. ``None`` disables caching.
    batch_size : int
        Batch size for encoding multiple texts at once.
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        device: Optional[str] = None,
        cache_dir: Optional[Path] = None,
        batch_size: int = 32,
    ) -> None:
        settings = get_settings()
        self._model_name = model_name or settings.retrieval.embedding_model
        self._dimension = settings.retrieval.embedding_dimension
        self._device = device or settings.embedding.device
        self._batch_size = batch_size
        self._cache_dir = Path(cache_dir) if cache_dir else None
        self._model: Optional[Any] = None
        self._loaded = False
        self._load_time_s = 0.0

    # ── Public API ──────────────────────────────

    @property
    def dimension(self) -> int:
        """Return the embedding vector dimension."""
        return self._dimension

    @property
    def model_name(self) -> str:
        return self._model_name

    def encode(self, text: str) -> List[float]:
        """Encode a single text string into a vector.

        Parameters
        ----------
        text : str
            The input text to encode.

        Returns
        -------
        List[float]
            The embedding vector.
        """
        return self.encode_batch([text])[0]

    def encode_batch(self, texts: List[str]) -> List[List[float]]:
        """Encode multiple texts into vectors in one call.

        Parameters
        ----------
        texts : List[str]
            Texts to encode.

        Returns
        -------
        List[List[float]]
            Embedding vectors in the same order as inputs.
        """
        if not texts:
            return []

        # Check cache for each text
        uncached_indices: List[int] = []
        uncached_texts: List[str] = []
        cached_results: Dict[int, List[float]] = {}

        if self._cache_dir:
            for i, text in enumerate(texts):
                cache_key = self._cache_key(text)
                cached = self._read_cache(cache_key)
                if cached is not None:
                    cached_results[i] = cached
                else:
                    uncached_indices.append(i)
                    uncached_texts.append(text)
        else:
            uncached_indices = list(range(len(texts)))
            uncached_texts = texts

        # Compute embeddings for uncached texts
        if uncached_texts:
            vectors = self._compute(uncached_texts)
            if self._cache_dir:
                for idx, vec in zip(uncached_indices, vectors):
                    cache_key = self._cache_key(texts[idx])
                    self._write_cache(cache_key, vec)
            for idx, vec in zip(uncached_indices, vectors):
                cached_results[idx] = vec

        return [cached_results[i] for i in range(len(texts))]

    def warmup(self) -> float:
        """Load the model into memory (idempotent).

        Returns
        -------
        float
            Time in seconds to load (0.0 if already loaded).
        """
        if self._loaded:
            return 0.0
        return self._load_model()

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    # ── Internal ────────────────────────────────

    def _load_model(self) -> float:
        if _HAS_SENTENCE_TRANSFORMERS:
            start = time.time()
            try:
                self._model = SentenceTransformer(
                    self._model_name,
                    device=self._device,
                )
                self._dimension = self._model.get_sentence_embedding_dimension()
                self._loaded = True
                elapsed = time.time() - start
                self._load_time_s = elapsed
                logger.info(
                    "EmbeddingGenerator: loaded model '{}' (dim={}, device={}) in {:.2f}s",
                    self._model_name,
                    self._dimension,
                    self._device,
                    elapsed,
                )
                return elapsed
            except Exception as exc:
                logger.warning(
                    "EmbeddingGenerator: failed to load model '{}': {}. "
                    "Using fallback encoding.",
                    self._model_name,
                    exc,
                )

        logger.warning("EmbeddingGenerator: sentence-transformers not installed, using fallback encoding")
        return 0.0

    def _compute(self, texts: List[str]) -> List[List[float]]:
        if not self._loaded:
            self._load_model()

        if self._model is not None:
            embeddings = self._model.encode(
                texts,
                batch_size=self._batch_size,
                show_progress_bar=False,
                normalize_embeddings=True,
            )
            return [emb.tolist() for emb in embeddings]

        return self._fallback_encode(texts)

    @staticmethod
    def _fallback_encode(texts: List[str]) -> List[List[float]]:
        """Deterministic hash-based fallback (for development only)."""
        import hashlib
        import struct

        dim = 384
        results: List[List[float]] = []
        for text in texts:
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            vec = []
            for i in range(dim):
                h = hashlib.sha256(digest + struct.pack("<I", i)).digest()
                val = struct.unpack("<I", h[:4])[0] / 4294967295.0
                vec.append(val)
            norm = sum(v * v for v in vec) ** 0.5
            if norm > 0:
                vec = [v / norm for v in vec]
            results.append(vec)
        return results

    @staticmethod
    def _cache_key(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]

    def _cache_path(self, key: str) -> Path:
        return (self._cache_dir / key).with_suffix(".vec")

    def _read_cache(self, key: str) -> Optional[List[float]]:
        path = self._cache_path(key)
        if path.exists():
            try:
                with open(path, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        return None

    def _write_cache(self, key: str, vector: List[float]) -> None:
        if self._cache_dir is None:
            return
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        try:
            with open(self._cache_path(key), "w") as f:
                json.dump(vector, f)
        except OSError as exc:
            logger.warning("EmbeddingGenerator: cache write failed: {}", exc)
