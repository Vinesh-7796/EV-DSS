"""Data models for the Knowledge Enrichment Engine.

Defines entities (Error Code, ECU, CAN Message, …), relationships,
canonical forms, and the enrichment report dataclass.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


# ──────────────────────────────────────────────
#  Entity type constants
# ──────────────────────────────────────────────

ENTITY_TYPE_ERROR_CODE = "error_code"
ENTITY_TYPE_CONNECTOR = "connector"
ENTITY_TYPE_ECU = "ecu"
ENTITY_TYPE_CAN_MESSAGE = "can_message"
ENTITY_TYPE_CAN_SIGNAL = "can_signal"
ENTITY_TYPE_SENSOR = "sensor"
ENTITY_TYPE_RELAY = "relay"
ENTITY_TYPE_FUSE = "fuse"
ENTITY_TYPE_COMPONENT = "component"
ENTITY_TYPE_SUBSYSTEM = "subsystem"
ENTITY_TYPE_PROCEDURE = "procedure"
ENTITY_TYPE_WARNING = "warning"
ENTITY_TYPE_MEASUREMENT = "measurement"

ALL_ENTITY_TYPES = frozenset({
    ENTITY_TYPE_ERROR_CODE,
    ENTITY_TYPE_CONNECTOR,
    ENTITY_TYPE_ECU,
    ENTITY_TYPE_CAN_MESSAGE,
    ENTITY_TYPE_CAN_SIGNAL,
    ENTITY_TYPE_SENSOR,
    ENTITY_TYPE_RELAY,
    ENTITY_TYPE_FUSE,
    ENTITY_TYPE_COMPONENT,
    ENTITY_TYPE_SUBSYSTEM,
    ENTITY_TYPE_PROCEDURE,
    ENTITY_TYPE_WARNING,
    ENTITY_TYPE_MEASUREMENT,
})

# ──────────────────────────────────────────────
#  Relationship type constants
# ──────────────────────────────────────────────

REL_CONNECTED_TO = "connected_to"
REL_CONTAINS = "contains"
REL_REFERENCES = "references"
REL_CONTROLS = "controls"
REL_MONITORS = "monitors"
REL_POWERED_BY = "powered_by"
REL_BELONGS_TO = "belongs_to"
REL_CAUSES = "causes"
REL_REQUIRES = "requires"
REL_MEASURES = "measures"
REL_LOCATED_IN = "located_in"

ALL_RELATIONSHIP_TYPES = frozenset({
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
})


# ──────────────────────────────────────────────
#  Entity
# ──────────────────────────────────────────────

@dataclass
class Entity:
    """A single entity extracted from a CDS document.

    Attributes
    ----------
    id : str
        Deterministic hash-based entity ID.
    type : str
        One of ``ENTITY_TYPE_*`` constants.
    name : str
        The extracted name (may be an alias).
    aliases : list of str
        Alternative names observed in the source document.
    source_node_id : str
        CDS ContentNode ID where this entity was found.
    source_document : str
        Source document filename.
    confidence : float
        Extraction confidence (0.0 – 1.0).
    metadata : dict
        Additional type-specific properties.
    """

    id: str = ""
    type: str = ""
    name: str = ""
    aliases: List[str] = field(default_factory=list)
    source_node_id: str = ""
    source_document: str = ""
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


# ──────────────────────────────────────────────
#  CanonicalEntity
# ──────────────────────────────────────────────

@dataclass
class CanonicalEntity:
    """A resolved canonical entity — all aliases merged into one record.

    Attributes
    ----------
    id : str
        Deterministic hash-based canonical ID.
    type : str
        Entity type.
    canonical_name : str
        The preferred / canonical name for this entity.
    aliases : list of str
        All known aliases (including the canonical name).
    entity_ids : list of str
        Original ``Entity.id`` values that were merged.
    source_documents : list of str
        All source documents where this entity appeared.
    relationships : list of EntityRelationship
        Relationships to other canonical entities.
    metadata : dict
        Aggregated metadata.
    """

    id: str = ""
    type: str = ""
    canonical_name: str = ""
    aliases: List[str] = field(default_factory=list)
    entity_ids: List[str] = field(default_factory=list)
    source_documents: List[str] = field(default_factory=list)
    relationships: List["EntityRelationship"] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


# ──────────────────────────────────────────────
#  EntityRelationship
# ──────────────────────────────────────────────

@dataclass
class EntityRelationship:
    """A relationship between two entities.

    Attributes
    ----------
    source_entity_id : str
        ID of the source entity or canonical entity.
    target_entity_id : str
        ID of the target entity or canonical entity.
    relationship_type : str
        One of ``REL_*`` constants.
    confidence : float
        Confidence in this relationship (0.0 – 1.0).
    metadata : dict
        Additional context (e.g. source document, evidence text).
    """

    source_entity_id: str = ""
    target_entity_id: str = ""
    relationship_type: str = ""
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


# ──────────────────────────────────────────────
#  EnrichmentReport
# ──────────────────────────────────────────────

@dataclass
class EnrichmentReport:
    """Outcome of a single Knowledge Enrichment run."""

    source_document: str = ""
    entities_extracted: int = 0
    entities_canonicalized: int = 0
    cross_document_links: int = 0
    relationships_discovered: int = 0
    validation_issues: List[str] = field(default_factory=list)
    enrichment_time_s: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def summary(self) -> str:
        status = "PASS" if not self.validation_issues else "FAIL"
        return (
            f"[{status}] {self.source_document}: "
            f"{self.entities_extracted} entities, "
            f"{self.relationships_discovered} relationships, "
            f"{self.cross_document_links} cross-links "
            f"in {self.enrichment_time_s:.2f}s"
        )

    def detailed(self) -> str:
        lines = [
            f"Source:           {self.source_document}",
            f"Entities found:   {self.entities_extracted}",
            f"Canonicalized:    {self.entities_canonicalized}",
            f"Cross-doc links:  {self.cross_document_links}",
            f"Relationships:    {self.relationships_discovered}",
            f"Time:             {self.enrichment_time_s:.2f}s",
            f"Timestamp:        {self.timestamp}",
        ]
        if self.validation_issues:
            lines.append(f"Issues ({len(self.validation_issues)}):")
            for issue in self.validation_issues[:10]:
                lines.append(f"  - {issue}")
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.summary()
