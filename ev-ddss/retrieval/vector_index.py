"""Vector Index — Qdrant-backed storage and semantic search for
embedded chunks.

Manages collection lifecycle (create, delete) and provides
vector search with metadata filtering.
"""

import time
from typing import Any, Dict, List, Optional, Tuple

from backend.logger import logger
from config import get_settings

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models as qdrant_models
    from qdrant_client.http.exceptions import UnexpectedResponse

    _HAS_QDRANT = True
except ImportError:
    _HAS_QDRANT = False
    QdrantClient = None  # type: ignore[assignment]
    qdrant_models = None  # type: ignore[assignment]


# Default collection name for semantic chunks
DEFAULT_COLLECTION = "semantic_chunks"


class VectorIndex:
    """Qdrant-based vector index for semantic chunk retrieval.

    Parameters
    ----------
    collection_name : str
        Qdrant collection name.
    vector_size : int
        Dimension of the embedding vectors.
    url : str
        Qdrant server URL (default from config).
    api_key : str or None
        Optional Qdrant API key.
    """

    def __init__(
        self,
        collection_name: str = DEFAULT_COLLECTION,
        vector_size: Optional[int] = None,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> None:
        settings = get_settings()
        self._collection_name = collection_name
        self._vector_size = vector_size or settings.retrieval.embedding_dimension
        self._url = url or settings.qdrant.url
        self._api_key = api_key or settings.qdrant.api_key
        self._client: Optional[QdrantClient] = None
        self._collection_ready = False

    # ── Connection & Lifecycle ──────────────────

    def connect(self) -> None:
        """Initialise the Qdrant client."""
        if not _HAS_QDRANT:
            raise RuntimeError("qdrant-client is not installed")
        self._client = QdrantClient(url=self._url, api_key=self._api_key, timeout=30)
        logger.info("VectorIndex: connected to Qdrant at {}", self._url)

    def disconnect(self) -> None:
        self._client = None
        self._collection_ready = False

    @property
    def is_connected(self) -> bool:
        return self._client is not None

    def ensure_collection(self) -> bool:
        """Create the collection if it does not exist.

        Returns True if the collection is ready.
        """
        if self._client is None:
            raise RuntimeError("VectorIndex: not connected. Call connect() first.")

        try:
            collections = self._client.get_collections().collections
            existing = {c.name for c in collections}
            if self._collection_name in existing:
                self._collection_ready = True
                return True
        except Exception:
            pass

        try:
            self._client.create_collection(
                collection_name=self._collection_name,
                vectors_config=qdrant_models.VectorParams(
                    size=self._vector_size,
                    distance=qdrant_models.Distance.COSINE,
                ),
                optimizers_config=qdrant_models.OptimizersConfigDiff(
                    indexing_threshold=10000,
                ),
            )
            self._collection_ready = True
            logger.info(
                "VectorIndex: created collection '{}' (dim={})",
                self._collection_name,
                self._vector_size,
            )
            return True
        except Exception as exc:
            logger.error("VectorIndex: collection creation failed: {}", exc)
            return False

    def delete_collection(self) -> bool:
        """Drop the entire collection."""
        if self._client is None:
            return False
        try:
            self._client.delete_collection(collection_name=self._collection_name)
            self._collection_ready = False
            logger.info("VectorIndex: deleted collection '{}'", self._collection_name)
            return True
        except Exception as exc:
            logger.error("VectorIndex: delete collection failed: {}", exc)
            return False

    # ── Indexing ────────────────────────────────

    def upsert(
        self,
        points: List[Tuple[str, List[float], Dict[str, Any]]],
        batch_size: int = 100,
    ) -> int:
        """Insert or update vector points.

        Parameters
        ----------
        points : list of (point_id, vector, payload) tuples
            The points to upsert.
        batch_size : int
            Number of points per batch.

        Returns
        -------
        int
            Number of points upserted.
        """
        if self._client is None:
            raise RuntimeError("VectorIndex: not connected")
        if not self._collection_ready:
            self.ensure_collection()

        qdrant_points = []
        for pid, vector, payload in points:
            qdrant_points.append(
                qdrant_models.PointStruct(
                    id=pid,
                    vector=vector,
                    payload=payload,
                )
            )

        total = 0
        for i in range(0, len(qdrant_points), batch_size):
            batch = qdrant_points[i : i + batch_size]
            try:
                self._client.upsert(
                    collection_name=self._collection_name,
                    points=batch,
                )
                total += len(batch)
            except Exception as exc:
                logger.error("VectorIndex: upsert batch failed at offset {}: {}", i, exc)

        logger.debug("VectorIndex: upserted {} points to '{}'", total, self._collection_name)
        return total

    def delete_points(self, point_ids: List[str]) -> int:
        """Delete points by ID."""
        if self._client is None:
            return 0
        if not self._collection_ready:
            self.ensure_collection()
        try:
            self._client.delete(
                collection_name=self._collection_name,
                points_selector=qdrant_models.PointIdsList(
                    points=point_ids,
                ),
            )
            return len(point_ids)
        except Exception as exc:
            logger.error("VectorIndex: delete points failed: {}", exc)
            return 0

    # ── Search ──────────────────────────────────

    def search(
        self,
        vector: List[float],
        top_k: int = 10,
        score_threshold: Optional[float] = None,
        filter_conditions: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Search for the nearest neighbours of a query vector.

        Parameters
        ----------
        vector : List[float]
            Query embedding vector.
        top_k : int
            Maximum number of results.
        score_threshold : float or None
            Minimum cosine similarity score.
        filter_conditions : dict or None
            Qdrant filter to apply (e.g. ``{"must": [{"key": "node_type", "match": {"value": "paragraph"}}]}``).

        Returns
        -------
        list of dict
            Each dict has keys: ``id``, ``score``, ``payload``, ``version``.
        """
        if self._client is None:
            raise RuntimeError("VectorIndex: not connected")
        if not self._collection_ready:
            self.ensure_collection()

        qdrant_filter = None
        if filter_conditions:
            qdrant_filter = qdrant_models.Filter(**filter_conditions)

        try:
            if hasattr(self._client, "search"):
                results = self._client.search(
                    collection_name=self._collection_name,
                    query_vector=vector,
                    limit=top_k,
                    score_threshold=score_threshold,
                    query_filter=qdrant_filter,
                    with_payload=True,
                )
            else:
                response = self._client.query_points(
                    collection_name=self._collection_name,
                    query=vector,
                    limit=top_k,
                    score_threshold=score_threshold,
                    query_filter=qdrant_filter,
                    with_payload=True,
                )
                results = response.points
            return [
                {
                    "id": hit.id,
                    "score": hit.score,
                    "payload": hit.payload or {},
                    "version": hit.version,
                }
                for hit in results
            ]
        except Exception as exc:
            logger.error("VectorIndex: search failed: {}", exc)
            return []

    def search_by_text(
        self,
        query_text: str,
        embedding_fn,
        top_k: int = 10,
        score_threshold: Optional[float] = None,
        filter_conditions: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Convenience: encode query text, then search.

        ``embedding_fn`` must accept a string and return ``List[float]``.
        """
        vector = embedding_fn(query_text)
        return self.search(
            vector=vector,
            top_k=top_k,
            score_threshold=score_threshold,
            filter_conditions=filter_conditions,
        )

    # ── Stats ───────────────────────────────────

    def count(self) -> int:
        """Return the number of points in the collection."""
        if self._client is None or not self._collection_ready:
            return 0
        try:
            result = self._client.count(
                collection_name=self._collection_name,
                exact=True,
            )
            return result.count
        except Exception:
            return 0

    def health_check(self) -> Dict[str, Any]:
        """Return health status information."""
        if self._client is None:
            return {"status": "disconnected"}
        info = {
            "status": "connected",
            "collection": self._collection_name,
            "collection_ready": self._collection_ready,
        }
        try:
            info["point_count"] = self.count()
        except Exception:
            info["point_count"] = -1
        return info
