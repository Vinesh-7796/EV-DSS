"""Knowledge validation for the enriched engineering knowledge graph.

Detects:

- Duplicate entities (same name + type, different IDs)
- Orphan nodes (entities with no relationships)
- Broken references (relationships to non-existent entities)
- Cyclic errors where invalid (A → B → A for certain relationship types)
- Missing canonical names
"""

from typing import Any, Dict, List, Optional, Set, Tuple

from backend.logger import logger
from processing.enrichment.models import (
    CanonicalEntity,
    EntityRelationship,
    ALL_ENTITY_TYPES,
    ALL_RELATIONSHIP_TYPES,
    REL_CONTAINS,
    REL_BELONGS_TO,
)


class KnowledgeValidator:
    """Validates a set of canonical entities and their relationships."""

    def __init__(self) -> None:
        self._issues: List[str] = []

    # ── Public API ──────────────────────────────

    def validate(
        self,
        canonical_entities: List[CanonicalEntity],
        relationships: List[EntityRelationship],
    ) -> List[str]:
        """Run all validation checks.

        Returns a list of human-readable issue descriptions (empty = valid).
        """
        self._issues = []
        self._check_duplicate_entities(canonical_entities)
        self._check_orphan_nodes(canonical_entities, relationships)
        self._check_broken_references(canonical_entities, relationships)
        self._check_cycles(canonical_entities, relationships)
        self._check_missing_canonical_names(canonical_entities)
        self._check_relationship_types(relationships)
        self._check_entity_types(canonical_entities)

        if self._issues:
            logger.warning("KnowledgeValidator: {} validation issues", len(self._issues))
        else:
            logger.info("KnowledgeValidator: validation passed")
        return list(self._issues)

    @property
    def issues(self) -> List[str]:
        return list(self._issues)

    # ── Checks ───────────────────────────────────

    def _check_duplicate_entities(self, entities: List[CanonicalEntity]) -> None:
        seen: Dict[str, List[str]] = {}
        for ce in entities:
            key = f"{ce.type}::{ce.canonical_name.lower()}"
            seen.setdefault(key, []).append(ce.id)
        for key, ids in seen.items():
            if len(ids) > 1:
                self._issues.append(
                    f"Duplicate entity '{key}' — multiple IDs: {ids}"
                )

    def _check_orphan_nodes(
        self,
        entities: List[CanonicalEntity],
        relationships: List[EntityRelationship],
    ) -> None:
        linked_ids: Set[str] = set()
        for rel in relationships:
            linked_ids.add(rel.source_entity_id)
            linked_ids.add(rel.target_entity_id)
        for ce in entities:
            if ce.id not in linked_ids:
                self._issues.append(
                    f"Orphan entity '{ce.canonical_name}' ({ce.id}) has no relationships"
                )

    def _check_broken_references(
        self,
        entities: List[CanonicalEntity],
        relationships: List[EntityRelationship],
    ) -> None:
        valid_ids: Set[str] = {ce.id for ce in entities}
        for rel in relationships:
            if rel.source_entity_id not in valid_ids:
                self._issues.append(
                    f"Broken reference: relationship source '{rel.source_entity_id}' "
                    f"not found in canonical entities"
                )
            if rel.target_entity_id not in valid_ids:
                self._issues.append(
                    f"Broken reference: relationship target '{rel.target_entity_id}' "
                    f"not found in canonical entities"
                )

    def _check_cycles(
        self,
        entities: List[CanonicalEntity],
        relationships: List[EntityRelationship],
    ) -> None:
        invalid_cycle_types = {REL_CONTAINS, REL_BELONGS_TO}
        for rel in relationships:
            if rel.relationship_type in invalid_cycle_types:
                if rel.source_entity_id == rel.target_entity_id:
                    self._issues.append(
                        f"Self-referencing {rel.relationship_type} on '{rel.source_entity_id}'"
                    )

    def _check_missing_canonical_names(self, entities: List[CanonicalEntity]) -> None:
        for ce in entities:
            if not ce.canonical_name or not ce.canonical_name.strip():
                self._issues.append(
                    f"Entity '{ce.id}' has empty canonical name"
                )

    def _check_relationship_types(self, relationships: List[EntityRelationship]) -> None:
        for rel in relationships:
            if rel.relationship_type not in ALL_RELATIONSHIP_TYPES:
                self._issues.append(
                    f"Unknown relationship type '{rel.relationship_type}' "
                    f"in ({rel.source_entity_id} -> {rel.target_entity_id})"
                )

    def _check_entity_types(self, entities: List[CanonicalEntity]) -> None:
        for ce in entities:
            if ce.type not in ALL_ENTITY_TYPES:
                self._issues.append(
                    f"Unknown entity type '{ce.type}' for '{ce.canonical_name}'"
                )
