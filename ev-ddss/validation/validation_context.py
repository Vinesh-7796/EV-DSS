from typing import Any, Dict, Optional, Set, List
from datetime import datetime

from validation.config import ValidationConfig


class ValidationContext:
    """Shared validation context providing optimized, batched Knowledge Base access.

    Maintains a snapshot of the Knowledge Base state to avoid repeated
    database queries across validators.
    """

    def __init__(self, knowledge_base: Any, config: ValidationConfig):
        self.knowledge_base = knowledge_base
        self.config = config
        self._entity_cache: Dict[str, Set[str]] = {}
        self._relationship_cache: Optional[Set[str]] = None
        self._cache_initialized = False
        self._cache_load_time_ms = 0.0

    def initialize(self):
        """Pre-load caches from the knowledge base for efficient batch access."""
        if self._cache_initialized:
            return

        start = datetime.now()

        if self.knowledge_base:
            try:
                from database.models import ContentNode, Edge
                from sqlalchemy import func

                # Batch load all content nodes
                nodes = self.knowledge_base.query(
                    ContentNode.type, ContentNode.id
                ).all()

                for node_type, node_id in nodes:
                    type_key = node_type.lower() if node_type else "unknown"
                    if type_key not in self._entity_cache:
                        self._entity_cache[type_key] = set()
                    self._entity_cache[type_key].add(node_id.lower())

                # Batch load all relationships
                edges = self.knowledge_base.query(
                    Edge.source, Edge.relationship_type, Edge.target
                ).all()

                rel_cache = set()
                for src, rel_type, tgt in edges:
                    rel_str = f"{src} {rel_type} {tgt}".lower()
                    rel_cache.add(rel_str)
                    rel_cache.add(f"{src.split()[-1] if src.split() else src} {rel_type} {tgt.split()[-1] if tgt.split() else tgt}".lower())

                self._relationship_cache = rel_cache

            except Exception:
                # KB not available — caches remain empty
                pass

        elapsed = (datetime.now() - start).total_seconds() * 1000
        self._cache_load_time_ms = elapsed
        self._cache_initialized = True

    def get_entity_cache(self) -> Dict[str, Set[str]]:
        """Get the entity cache, initializing if needed."""
        if not self._cache_initialized:
            self.initialize()
        return self._entity_cache

    def get_relationship_cache(self) -> Optional[Set[str]]:
        """Get the relationship cache, initializing if needed."""
        if not self._cache_initialized:
            self.initialize()
        return self._relationship_cache

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for logging."""
        entity_count = sum(len(v) for v in self._entity_cache.values())
        relationship_count = len(self._relationship_cache) if self._relationship_cache else 0
        return {
            "initialized": self._cache_initialized,
            "entity_types": len(self._entity_cache),
            "entity_count": entity_count,
            "relationship_count": relationship_count,
            "load_time_ms": self._cache_load_time_ms,
        }