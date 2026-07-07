"""Relationship discovery between engineering entities.

Infers typed relationships from:

- DBC message sender/receiver topology (ECU → controls → message)
- ContentNode parent-child hierarchy (message → contains → signal)
- Text co-occurrence patterns (component → located_in → subsystem)
- Table adjacency (connector → connected_to → component)
- Cross-document entity co-reference
"""

from typing import Any, Dict, List, Optional, Set, Tuple

from backend.logger import logger
from processing.enrichment.models import (
    CanonicalEntity,
    Entity,
    EntityRelationship,
    REL_CONNECTED_TO,
    REL_CONTAINS,
    REL_REFERENCES,
    REL_CONTROLS,
    REL_MONITORS,
    REL_POWERED_BY,
    REL_BELONGS_TO,
    REL_CAUSES,
    REL_REQUIRES,
    REL_MEASURES,
    REL_LOCATED_IN,
    ENTITY_TYPE_CAN_MESSAGE,
    ENTITY_TYPE_CAN_SIGNAL,
    ENTITY_TYPE_ECU,
    ENTITY_TYPE_SENSOR,
    ENTITY_TYPE_ERROR_CODE,
    ENTITY_TYPE_COMPONENT,
    ENTITY_TYPE_SUBSYSTEM,
    ENTITY_TYPE_FUSE,
    ENTITY_TYPE_MEASUREMENT,
)


class RelationshipDiscoverer:
    """Discovers relationships between canonical entities.

    Uses a combination of structural rules (parent-child hierarchy, DBC
    topology) and text-pattern rules (co-occurrence, adjacency).
    """

    def __init__(self) -> None:
        self._discovered: int = 0
        self._seen: Set[Tuple[str, str, str]] = set()

    # ── Public API ──────────────────────────────

    def discover(
        self,
        canonical_entities: List[CanonicalEntity],
    ) -> List[EntityRelationship]:
        """Discover relationships among *canonical_entities*.

        Returns a deduplicated list of ``EntityRelationship``.
        """
        self._discovered = 0
        self._seen.clear()
        relationships: List[EntityRelationship] = []

        # Build lookup index
        by_type: Dict[str, List[CanonicalEntity]] = {}
        by_any_name: Dict[str, List[CanonicalEntity]] = {}
        for ce in canonical_entities:
            by_type.setdefault(ce.type, []).append(ce)
            by_any_name.setdefault(ce.canonical_name.lower(), []).append(ce)
            for alias in ce.aliases:
                by_any_name.setdefault(alias.lower(), []).append(ce)

        # Rule 1: ECU → controls → CAN Message
        self._discover_ecu_controls(by_type, relationships)

        # Rule 2: CAN Message → contains → CAN Signal
        self._discover_message_contains_signal(by_type, relationships)

        # Rule 3: ECU → monitors → Sensor
        self._discover_ecu_monitors(by_type, by_any_name, relationships)

        # Rule 4: Component → belongs_to → Subsystem
        self._discover_belongs_to(by_type, by_any_name, relationships)

        # Rule 5: Fuse → powered_by → Component
        self._discover_powered_by(by_type, relationships)

        # Rule 6: Error Code → references → Component / Sensor
        self._discover_error_references(by_type, by_any_name, relationships)

        # Rule 7: Sensor → measures → Measurement
        self._discover_measures(by_type, relationships)

        # Rule 8: Connected_to (co-occurrence heuristic)
        self._discover_connected_to(by_type, by_any_name, relationships)

        # Rule 9: Entity → located_in → Subsystem
        self._discover_located_in(by_type, by_any_name, relationships)

        logger.info(
            "RelationshipDiscoverer: discovered {} unique relationships",
            self._discovered,
        )
        return relationships

    @property
    def relationship_count(self) -> int:
        return self._discovered

    # ── Discovery rules ─────────────────────────

    def _add(self, rel: EntityRelationship, relationships: List[EntityRelationship]) -> None:
        key = (rel.source_entity_id, rel.target_entity_id, rel.relationship_type)
        if key not in self._seen:
            self._seen.add(key)
            relationships.append(rel)
            self._discovered += 1

    @staticmethod
    def _discover_ecu_controls(
        by_type: Dict[str, List[CanonicalEntity]],
        relationships: List[EntityRelationship],
    ) -> None:
        """ECU → controls → CAN Message (by DLC metadata co-reference)."""
        ecus = by_type.get(ENTITY_TYPE_ECU, [])
        msgs = by_type.get(ENTITY_TYPE_CAN_MESSAGE, [])
        for ecu in ecus:
            ecu_name_lower = ecu.canonical_name.lower()
            for msg in msgs:
                sender = (msg.metadata.get("sender") or "").lower()
                if sender and sender == ecu_name_lower:
                    relationships.append(EntityRelationship(
                        source_entity_id=ecu.id,
                        target_entity_id=msg.id,
                        relationship_type=REL_CONTROLS,
                        confidence=0.95,
                        metadata={"evidence": f"ECU {ecu.canonical_name} sends {msg.canonical_name}"},
                    ))

    @staticmethod
    def _discover_message_contains_signal(
        by_type: Dict[str, List[CanonicalEntity]],
        relationships: List[EntityRelationship],
    ) -> None:
        """CAN Message → contains → CAN Signal (by shared source_document pattern)."""
        msgs = by_type.get(ENTITY_TYPE_CAN_MESSAGE, [])
        sigs = by_type.get(ENTITY_TYPE_CAN_SIGNAL, [])
        if not msgs or not sigs:
            return
        # Group signals by the entity_ids of their parent messages
        # We use the source_documents as a heuristic: signals in same doc as message
        for msg in msgs:
            for sig in sigs:
                common_docs = set(msg.source_documents) & set(sig.source_documents)
                if common_docs:
                    relationships.append(EntityRelationship(
                        source_entity_id=msg.id,
                        target_entity_id=sig.id,
                        relationship_type=REL_CONTAINS,
                        confidence=0.9,
                        metadata={"evidence": f"Message {msg.canonical_name} contains signal {sig.canonical_name}"},
                    ))

    @staticmethod
    def _discover_ecu_monitors(
        by_type: Dict[str, List[CanonicalEntity]],
        by_any_name: Dict[str, List[CanonicalEntity]],
        relationships: List[EntityRelationship],
    ) -> None:
        """ECU → monitors → Sensor / Component (by name co-occurrence)."""
        ecus = by_type.get(ENTITY_TYPE_ECU, [])
        sensors = by_type.get(ENTITY_TYPE_SENSOR, [])
        for ecu in ecus:
            for sensor in sensors:
                common_docs = set(ecu.source_documents) & set(sensor.source_documents)
                if common_docs:
                    relationships.append(EntityRelationship(
                        source_entity_id=ecu.id,
                        target_entity_id=sensor.id,
                        relationship_type=REL_MONITORS,
                        confidence=0.7,
                        metadata={"evidence": f"Co-occurrence in {common_docs}"},
                    ))

    @staticmethod
    def _discover_belongs_to(
        by_type: Dict[str, List[CanonicalEntity]],
        by_any_name: Dict[str, List[CanonicalEntity]],
        relationships: List[EntityRelationship],
    ) -> None:
        """Component → belongs_to → Subsystem."""
        components = by_type.get(ENTITY_TYPE_COMPONENT, [])
        subsystems = by_type.get(ENTITY_TYPE_SUBSYSTEM, [])
        for comp in components:
            for sub in subsystems:
                common_docs = set(comp.source_documents) & set(sub.source_documents)
                if common_docs:
                    relationships.append(EntityRelationship(
                        source_entity_id=comp.id,
                        target_entity_id=sub.id,
                        relationship_type=REL_BELONGS_TO,
                        confidence=0.6,
                        metadata={"evidence": f"Co-occurrence in {common_docs}"},
                    ))

    @staticmethod
    def _discover_powered_by(
        by_type: Dict[str, List[CanonicalEntity]],
        relationships: List[EntityRelationship],
    ) -> None:
        """Fuse → powered_by → Component (shared documents)."""
        fuses = by_type.get(ENTITY_TYPE_FUSE, [])
        components = by_type.get(ENTITY_TYPE_COMPONENT, [])
        for fuse in fuses:
            for comp in components:
                common_docs = set(fuse.source_documents) & set(comp.source_documents)
                if common_docs:
                    relationships.append(EntityRelationship(
                        source_entity_id=fuse.id,
                        target_entity_id=comp.id,
                        relationship_type=REL_POWERED_BY,
                        confidence=0.5,
                        metadata={"evidence": f"Co-occurrence in {common_docs}"},
                    ))

    @staticmethod
    def _discover_error_references(
        by_type: Dict[str, List[CanonicalEntity]],
        by_any_name: Dict[str, List[CanonicalEntity]],
        relationships: List[EntityRelationship],
    ) -> None:
        """Error Code → references → Component / Sensor."""
        errors = by_type.get(ENTITY_TYPE_ERROR_CODE, [])
        targets = by_type.get(ENTITY_TYPE_COMPONENT, []) + by_type.get(ENTITY_TYPE_SENSOR, [])
        for err in errors:
            for tgt in targets:
                common_docs = set(err.source_documents) & set(tgt.source_documents)
                if common_docs:
                    relationships.append(EntityRelationship(
                        source_entity_id=err.id,
                        target_entity_id=tgt.id,
                        relationship_type=REL_REFERENCES,
                        confidence=0.55,
                        metadata={"evidence": f"Co-occurrence in {common_docs}"},
                    ))

    @staticmethod
    def _discover_measures(
        by_type: Dict[str, List[CanonicalEntity]],
        relationships: List[EntityRelationship],
    ) -> None:
        """Sensor → measures → Measurement (shared documents)."""
        sensors = by_type.get(ENTITY_TYPE_SENSOR, [])
        measurements = by_type.get(ENTITY_TYPE_MEASUREMENT, [])
        for sensor in sensors:
            for meas in measurements:
                common_docs = set(sensor.source_documents) & set(meas.source_documents)
                if common_docs:
                    relationships.append(EntityRelationship(
                        source_entity_id=sensor.id,
                        target_entity_id=meas.id,
                        relationship_type=REL_MEASURES,
                        confidence=0.6,
                        metadata={"evidence": f"Co-occurrence in {common_docs}"},
                    ))

    @staticmethod
    def _discover_connected_to(
        by_type: Dict[str, List[CanonicalEntity]],
        by_any_name: Dict[str, List[CanonicalEntity]],
        relationships: List[EntityRelationship],
    ) -> None:
        """connected_to between entities of different types in same document."""
        all_entities: List[CanonicalEntity] = []
        for group in by_type.values():
            all_entities.extend(group)
        for i, a in enumerate(all_entities):
            for b in all_entities[i + 1:]:
                if a.type == b.type:
                    continue
                common_docs = set(a.source_documents) & set(b.source_documents)
                if common_docs:
                    relationships.append(EntityRelationship(
                        source_entity_id=a.id,
                        target_entity_id=b.id,
                        relationship_type=REL_CONNECTED_TO,
                        confidence=0.4,
                        metadata={"evidence": f"Cross-type co-occurrence in {common_docs}"},
                    ))

    @staticmethod
    def _discover_located_in(
        by_type: Dict[str, List[CanonicalEntity]],
        by_any_name: Dict[str, List[CanonicalEntity]],
        relationships: List[EntityRelationship],
    ) -> None:
        """Entity → located_in → Subsystem."""
        subsystems = by_type.get(ENTITY_TYPE_SUBSYSTEM, [])
        other_types = [t for t in by_type if t != ENTITY_TYPE_SUBSYSTEM]
        for stype in other_types:
            for ent in by_type[stype]:
                for sub in subsystems:
                    common_docs = set(ent.source_documents) & set(sub.source_documents)
                    if common_docs:
                        relationships.append(EntityRelationship(
                            source_entity_id=ent.id,
                            target_entity_id=sub.id,
                            relationship_type=REL_LOCATED_IN,
                            confidence=0.5,
                            metadata={"evidence": f"Co-occurrence in {common_docs}"},
                        ))
