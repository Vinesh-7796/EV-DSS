"""Qdrant vector database connectivity for EV-DDSS.

Provides connection management, health checks, and collection listing.
No collections are created during Phase 0.
"""

from typing import Any, Dict, List, Optional

from qdrant_client import QdrantClient as _QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse

from backend.logger import logger
from config import get_settings


class QdrantManager:
    """Manages the Qdrant vector database connection.

    Usage:
        qdrant = QdrantManager()
        qdrant.connect()
        health = qdrant.health_check()
        collections = qdrant.list_collections()
    """

    def __init__(self, url: Optional[str] = None, api_key: Optional[str] = None) -> None:
        """Initialize the Qdrant manager.

        Args:
            url: Qdrant server URL. Uses settings if not provided.
            api_key: Optional API key for authentication.
        """
        settings = get_settings()
        self._url: str = url or settings.qdrant.url
        self._api_key: Optional[str] = api_key or settings.qdrant.api_key
        self._client: Optional[_QdrantClient] = None
        self._connected: bool = False

    @property
    def is_connected(self) -> bool:
        """Whether the Qdrant client is initialized and connected."""
        return self._connected

    def connect(self) -> None:
        """Initialize the Qdrant client and verify the connection.

        Raises:
            ConnectionError: If the Qdrant server is unreachable.
        """
        try:
            self._client = _QdrantClient(
                url=self._url,
                api_key=self._api_key,
                timeout=30,
            )
            # Verify connection by fetching collection list
            self._client.get_collections()
            self._connected = True
            logger.info("Qdrant connection verified successfully at {}", self._url)
        except Exception as exc:
            self._connected = False
            logger.error("Qdrant connection failed: {}", exc)
            raise ConnectionError(f"Qdrant connection failed: {exc}") from exc

    def disconnect(self) -> None:
        """Close the Qdrant client connection."""
        if self._client is not None:
            self._client = None
            self._connected = False
            logger.info("Qdrant connection closed")

    def health_check(self) -> Dict[str, Any]:
        """Perform a Qdrant health check.

        Returns:
            Dictionary with health status information.
        """
        if self._client is None or not self._connected:
            return {"status": "disconnected", "error": "No active connection"}

        try:
            collections = self._client.get_collections()
            collection_names = [c.name for c in collections.collections]
            return {
                "status": "healthy",
                "url": self._url,
                "collections": collection_names,
                "collection_count": len(collection_names),
            }
        except UnexpectedResponse as exc:
            return {"status": "unhealthy", "error": str(exc)}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    def list_collections(self) -> List[str]:
        """List all existing Qdrant collections.

        Returns:
            List of collection names.
        """
        if self._client is None:
            raise RuntimeError("Qdrant not connected. Call connect() first.")

        collections = self._client.get_collections()
        return [c.name for c in collections.collections]


# Module-level singleton
_qdrant_manager: Optional[QdrantManager] = None


def get_qdrant() -> QdrantManager:
    """Return the global QdrantManager singleton.

    Returns:
        The QdrantManager instance.
    """
    global _qdrant_manager
    if _qdrant_manager is None:
        _qdrant_manager = QdrantManager()
    return _qdrant_manager
