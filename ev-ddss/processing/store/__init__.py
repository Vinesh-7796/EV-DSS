"""Knowledge Store abstraction for persisting CDS Documents.

Provides a generic ``KnowledgeStore`` ABC with filesystem, SQL, and
image implementations.  The ``KnowledgeStoreManager`` orchestrates
multiple stores so that a single document can be persisted everywhere.
"""

from processing.store.base import KnowledgeStore
from processing.store.json_store import JSONKnowledgeStore
from processing.store.sql_store import PostgreSQLKnowledgeStore
from processing.store.image_store import ImageStore
from processing.store.manager import KnowledgeStoreManager

__all__ = [
    "KnowledgeStore",
    "JSONKnowledgeStore",
    "PostgreSQLKnowledgeStore",
    "ImageStore",
    "KnowledgeStoreManager",
]
