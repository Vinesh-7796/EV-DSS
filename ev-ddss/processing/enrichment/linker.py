"""Cross-document entity linking.

Matches entities discovered in different documents that share the same
canonical name and type, merging them into shared ``CanonicalEntity``
records.
"""

from typing import Any, Dict, List, Optional

from backend.logger import logger
from processing.enrichment.models import (
    CanonicalEntity,
    Entity,
    EntityRelationship,
    ALL_ENTITY_TYPES,
    REL_REFERENCES,
)


class CrossDocumentLinker:
    """Links canonical entities across multiple documents.

    When the same canonical entity appears in two or more documents,
    the linker merges their ``source_documents`` lists, collects
    aliases from all occurrences, and creates ``references``
    relationships between them.
    """

    def __init__(self) -> None:
        self._cross_links: int = 0

    # ── Public API ──────────────────────────────

    def link(
        self,
        existing_canonical: List[CanonicalEntity],
        new_canonical: List[CanonicalEntity],
    ) -> List[CanonicalEntity]:
        """Merge *new_canonical* entities into *existing_canonical*.

        Entities with matching ``canonical_name`` and ``type`` are merged.
        New entities that don't match any existing one are appended.

        Returns the merged list of canonical entities.
        """
        self._cross_links = 0
        index: Dict[str, CanonicalEntity] = {}
        for ce in existing_canonical:
            key = f"{ce.type}::{ce.canonical_name}"
            index[key] = ce

        for ce in new_canonical:
            key = f"{ce.type}::{ce.canonical_name}"
            if key in index:
                existing = index[key]
                self._merge(existing, ce)
            else:
                index[key] = ce

        result = list(index.values())
        logger.info(
            "CrossDocumentLinker: {} cross-document links from {} new entities",
            self._cross_links,
            len(new_canonical),
        )
        return result

    @property
    def cross_link_count(self) -> int:
        return self._cross_links

    # ── Internal ────────────────────────────────

    @staticmethod
    def _merge(target: CanonicalEntity, source: CanonicalEntity) -> None:
        """Merge *source* into *target*."""
        for alias in source.aliases:
            if alias not in target.aliases and alias != target.canonical_name:
                target.aliases.append(alias)

        for eid in source.entity_ids:
            if eid not in target.entity_ids:
                target.entity_ids.append(eid)

        for doc in source.source_documents:
            if doc not in target.source_documents:
                target.source_documents.append(doc)

        target.aliases.sort()
        target.source_documents.sort()
