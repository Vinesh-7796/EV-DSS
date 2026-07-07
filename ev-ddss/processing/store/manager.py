"""Orchestrates multiple KnowledgeStore implementations.

The Processing Engine and Document Intelligence Pipeline communicate
only through the ``KnowledgeStoreManager`` — they never talk to
individual filesystem, SQL, or image stores directly.
"""

from typing import Any, Dict, List, Optional

from backend.logger import logger
from processing.models.models import Document
from processing.store.base import KnowledgeStore


class KnowledgeStoreManager:
    """Manages a collection of ``KnowledgeStore`` instances.

    When ``store_across_all`` is called, the document is persisted in
    *every* registered store.  Individual stores can be accessed via
    ``get_store()`` for targeted operations.
    """

    def __init__(self) -> None:
        self._stores: Dict[str, KnowledgeStore] = {}

    # ── Registration ────────────────────────────

    def register(self, name: str, store: KnowledgeStore) -> None:
        """Register a store implementation under a logical name."""
        self._stores[name] = store
        logger.debug("KnowledgeStoreManager: registered store '{}' ({})", name, store.name)

    def register_defaults(self) -> None:
        """Register the built-in JSON and Image stores."""
        from processing.store.json_store import JSONKnowledgeStore
        from processing.store.image_store import ImageStore

        self.register("json", JSONKnowledgeStore())
        self.register("image", ImageStore())

        try:
            from processing.store.sql_store import PostgreSQLKnowledgeStore

            sql_store = PostgreSQLKnowledgeStore()
            if sql_store.health_check():
                self.register("postgresql", sql_store)
                logger.info("KnowledgeStoreManager: PostgreSQL store connected")
            else:
                logger.info("KnowledgeStoreManager: PostgreSQL unavailable, skipping")
        except ImportError:
            logger.info("KnowledgeStoreManager: SQLAlchemy not installed, skipping PostgreSQL store")
        except Exception as exc:
            logger.info("KnowledgeStoreManager: PostgreSQL store skipped ({})", exc)

    # ── Operations ──────────────────────────────

    def store_across_all(self, document: Document, source_id: str = "") -> Dict[str, str]:
        """Persist a CDS Document in every registered store.

        Returns a dict mapping store names to store-specific identifiers.
        """
        results: Dict[str, str] = {}
        for name, store in self._stores.items():
            try:
                store_id = store.store(document, source_id)
                results[name] = store_id
            except Exception as exc:
                logger.error("KnowledgeStoreManager: '{}' store failed for {}: {}", name, document.source, exc)
                results[name] = ""
        return results

    def get_store(self, name: str) -> KnowledgeStore:
        """Return a registered store by name."""
        if name not in self._stores:
            raise ValueError(
                f"Store '{name}' not registered. Available stores: {list(self._stores.keys())}"
            )
        return self._stores[name]

    def list_all(self) -> Dict[str, List[Dict[str, Any]]]:
        """List documents in every registered store."""
        result: Dict[str, List[Dict[str, Any]]] = {}
        for name, store in self._stores.items():
            try:
                result[name] = store.list_documents()
            except Exception:
                result[name] = []
        return result

    @property
    def store_names(self) -> List[str]:
        """Names of all registered stores."""
        return list(self._stores.keys())

    @property
    def store_count(self) -> int:
        """Number of registered stores."""
        return len(self._stores)
