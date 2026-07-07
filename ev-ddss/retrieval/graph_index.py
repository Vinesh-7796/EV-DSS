"""Graph Index — builds a traversable in-memory graph from the
RelationshipGraph and CanonicalEntityIndex for multi-hop traversal.

Supports breadth-first and depth-first traversal, neighbourhood
expansion, and entity-to-content-node bridging.
"""

from collections import deque
import time
from typing import Any, Dict, List, Optional, Set

from backend.logger import logger
from processing.enrichment.index import CanonicalEntityIndex
from processing.enrichment.models import (
    ALL_RELATIONSHIP_TYPES,
    CanonicalEntity,
    EntityRelationship,
)


class GraphIndex:
    """In-memory graph index for multi-hop entity-relationship traversal.

    Builds a bidirectional adjacency list from the canonical entity
    index enriched documents' relationship graphs, enabling queries
    like "find all entities related to X within 2 hops".

    Parameters
    ----------
    entity_index : CanonicalEntityIndex or None
        Loaded canonical entity index. If None, a new one is created.
    """

    def __init__(self, entity_index: Optional[CanonicalEntityIndex] = None) -> None:
        self._entity_index = entity_index or CanonicalEntityIndex()
        self._entities: Dict[str, CanonicalEntity] = {}
        self._adjacency: Dict[str, List[EntityRelationship]] = {}
        self._entity_by_name: Dict[str, str] = {}
        self._loaded = False

    # ── Build / Load ────────────────────────────

    def build(self, entities: List[CanonicalEntity]) -> None:
        """Build the graph from a list of canonical entities."""
        self._entities = {e.id: e for e in entities}
        self._adjacency = {e.id: [] for e in entities}
        self._entity_by_name = {}

        for entity in entities:
            self._entity_by_name[entity.canonical_name.lower()] = entity.id
            for alias in entity.aliases:
                self._entity_by_name[alias.lower()] = entity.id
            for rel in entity.relationships:
                self._adjacency.setdefault(rel.source_entity_id, []).append(rel)
                # Add reverse edge for bidirectional traversal
                reverse_rel = EntityRelationship(
                    source_entity_id=rel.target_entity_id,
                    target_entity_id=rel.source_entity_id,
                    relationship_type=rel.relationship_type,
                    confidence=rel.confidence,
                    metadata=rel.metadata,
                )
                self._adjacency.setdefault(rel.target_entity_id, []).append(reverse_rel)

        self._loaded = True
        logger.debug("GraphIndex: built with {} entities, {} adjacency entries", len(entities), len(self._adjacency))

    def load_from_index(self) -> bool:
        """Load entities from the persistent ``CanonicalEntityIndex``."""
        try:
            entities = self._entity_index.load()
            if entities:
                self.build(entities)
                return True
            return False
        except Exception as exc:
            logger.warning("GraphIndex: failed to load entity index: {}", exc)
            return False

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def entity_count(self) -> int:
        return len(self._entities)

    @property
    def edge_count(self) -> int:
        return sum(len(edges) for edges in self._adjacency.values()) // 2  # deduplicate bidirectional

    # ── Lookup ──────────────────────────────────

    def lookup_entity(self, entity_id: str) -> Optional[CanonicalEntity]:
        """Look up an entity by its canonical ID."""
        return self._entities.get(entity_id)

    def find_entity_by_name(self, name: str) -> Optional[CanonicalEntity]:
        """Find an entity by its canonical name or alias (case-insensitive)."""
        eid = self._entity_by_name.get(name.lower().strip())
        if eid:
            return self._entities.get(eid)
        return None

    def search_entities(self, query: str) -> List[CanonicalEntity]:
        """Search entities by name/alias substring."""
        q = query.lower()
        results: List[CanonicalEntity] = []
        for entity in self._entities.values():
            if q in entity.canonical_name.lower():
                results.append(entity)
                continue
            for alias in entity.aliases:
                if q in alias.lower():
                    results.append(entity)
                    break
        return results

    def search(self, query: str, top_k: int = 10, max_hops: int = 2) -> List[Dict[str, Any]]:
        """Compatibility search API for graph retrieval.

        Older retrieval orchestration expects ``GraphIndex.search(query)``.
        The graph index's native query flow is entity substring matching
        followed by relationship traversal, so this wrapper preserves that
        contract without changing the graph layer.
        """
        start = time.time()
        if not self._loaded:
            self.load_from_index()

        seed_entities = self.search_entities(query)
        seed_ids = [entity.id for entity in seed_entities]
        traversed = self.traverse(seed_ids, max_hops=max_hops) if seed_ids else []
        results = self._dedupe_search_results(traversed)[:top_k]
        relationship_count = sum(len(item.get("path", [])) for item in results)
        latency_ms = (time.time() - start) * 1000

        print(f"Graph initialized: {'YES' if self._loaded else 'NO'}")
        print(f"Graph connected: {'YES' if self.edge_count > 0 else 'NO'}")
        print("Method invoked: GraphIndex.search -> search_entities + traverse")
        print(f"Returned nodes: {len(results)}")
        print(f"Returned relationships: {relationship_count}")
        print(f"Latency: {latency_ms:.3f} ms")
        logger.info(
            "Graph retrieval: initialized={} connected={} method={} nodes={} relationships={} latency_ms={:.3f}",
            self._loaded,
            self.edge_count > 0,
            "GraphIndex.search -> search_entities + traverse",
            len(results),
            relationship_count,
            latency_ms,
        )

        return results

    # ── Traversal ───────────────────────────────

    def traverse(
        self,
        seed_entity_ids: List[str],
        max_hops: int = 2,
        relationship_types: Optional[Set[str]] = None,
        min_confidence: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """Traverse the graph starting from seed entity IDs.

        Breadth-first traversal up to ``max_hops``.

        Returns
        -------
        list of dict
            Each entry: ``{"entity": CanonicalEntity, "hops": int, "path": [relationship_types]}``
        """
        if not self._loaded or not seed_entity_ids:
            return []

        visited: Set[str] = set(seed_entity_ids)
        queue: deque = deque()
        results: List[Dict[str, Any]] = []

        for sid in seed_entity_ids:
            entity = self._entities.get(sid)
            if entity:
                results.append({"entity": entity, "hops": 0, "path": []})
                queue.append((sid, 0, []))

        while queue:
            current_id, hops, path = queue.popleft()
            if hops >= max_hops:
                continue

            for rel in self._adjacency.get(current_id, []):
                if rel.confidence < min_confidence:
                    continue
                if relationship_types and rel.relationship_type not in relationship_types:
                    continue

                target_id = rel.target_entity_id
                if target_id not in visited and target_id in self._entities:
                    visited.add(target_id)
                    new_path = path + [rel.relationship_type]
                    entity = self._entities[target_id]
                    results.append({"entity": entity, "hops": hops + 1, "path": new_path})
                    queue.append((target_id, hops + 1, new_path))

        return results

    def traverse_from_name(
        self,
        entity_name: str,
        max_hops: int = 2,
    ) -> List[Dict[str, Any]]:
        """Convenience: find entity by name and traverse."""
        entity = self.find_entity_by_name(entity_name)
        if entity is None:
            return []
        return self.traverse([entity.id], max_hops=max_hops)

    def get_neighbourhood(
        self,
        entity_id: str,
        max_hops: int = 1,
    ) -> Dict[str, Any]:
        """Return the full neighbourhood of an entity as a serialisable dict."""
        entity = self._entities.get(entity_id)
        if entity is None:
            return {"center": None, "neighbours": []}

        neighbours = self.traverse([entity_id], max_hops=max_hops)
        return {
            "center": {
                "id": entity.id,
                "type": entity.type,
                "name": entity.canonical_name,
                "aliases": entity.aliases,
            },
            "neighbours": [
                {
                    "id": n["entity"].id,
                    "type": n["entity"].type,
                    "name": n["entity"].canonical_name,
                    "hops": n["hops"],
                    "relationship_path": n["path"],
                }
                for n in neighbours
                if n["hops"] > 0
            ],
        }

    @staticmethod
    def _dedupe_search_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        deduped: List[Dict[str, Any]] = []
        seen: Set[str] = set()
        for result in results:
            entity = result.get("entity")
            entity_id = getattr(entity, "id", "")
            if not entity_id or entity_id in seen:
                continue
            seen.add(entity_id)
            deduped.append(result)
        return deduped
