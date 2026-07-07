"""Abstract base class for all KnowledgeStore implementations.

The Processing Engine and Document Intelligence Pipeline communicate
only through this interface — they never interact with filesystems,
SQL databases, or cloud storage directly.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from processing.models.models import Document


class KnowledgeStore(ABC):
    """Generic abstraction for persisting CDS Document objects.

    Every implementation must provide ``store``, ``retrieve``,
    ``list_documents``, ``delete``, and ``health_check``.
    """

    @abstractmethod
    def store(self, document: Document, source_id: str = "") -> str:
        """Persist a CDS Document and return a store-specific identifier."""
        ...

    @abstractmethod
    def retrieve(self, store_id: str) -> Optional[Document]:
        """Load a CDS Document by its store identifier.

        Returns None when the document does not exist.
        """
        ...

    @abstractmethod
    def list_documents(self) -> List[Dict[str, Any]]:
        """Return summary metadata for every stored document.

        Each entry should contain at least ``store_id``, ``source``,
        ``type``, and ``stored_at``.
        """
        ...

    @abstractmethod
    def delete(self, store_id: str) -> bool:
        """Remove a stored document.  Returns True on success."""
        ...

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if the store is accessible and operational."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable store name (e.g. ``"json"``, ``"postgresql"``)."""
        ...
