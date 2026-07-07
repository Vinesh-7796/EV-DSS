"""Knowledge Enrichment Engine for EV-DDSS.

Transforms processed CDS documents into an engineering knowledge graph by
resolving entities, normalizing terminology, and linking information across
multiple documents.
"""

from processing.enrichment.models import (
    Entity,
    CanonicalEntity,
    EntityRelationship,
    EnrichmentReport,
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
)
from processing.enrichment.extractor import EntityExtractor
from processing.enrichment.canonicalizer import Canonicalizer
from processing.enrichment.linker import CrossDocumentLinker
from processing.enrichment.discoverer import RelationshipDiscoverer
from processing.enrichment.enricher import GraphEnricher
from processing.enrichment.validator import KnowledgeValidator
from processing.enrichment.index import CanonicalEntityIndex, AliasDictionary
from processing.enrichment.pipeline import KnowledgeEnrichmentPipeline

__all__ = [
    "Entity",
    "CanonicalEntity",
    "EntityRelationship",
    "EnrichmentReport",
    "EntityExtractor",
    "Canonicalizer",
    "CrossDocumentLinker",
    "RelationshipDiscoverer",
    "GraphEnricher",
    "KnowledgeValidator",
    "CanonicalEntityIndex",
    "AliasDictionary",
    "KnowledgeEnrichmentPipeline",
    # Constants
    "ENTITY_TYPE_ERROR_CODE",
    "ENTITY_TYPE_CONNECTOR",
    "ENTITY_TYPE_ECU",
    "ENTITY_TYPE_CAN_MESSAGE",
    "ENTITY_TYPE_CAN_SIGNAL",
    "ENTITY_TYPE_SENSOR",
    "ENTITY_TYPE_RELAY",
    "ENTITY_TYPE_FUSE",
    "ENTITY_TYPE_COMPONENT",
    "ENTITY_TYPE_SUBSYSTEM",
    "ENTITY_TYPE_PROCEDURE",
    "ENTITY_TYPE_WARNING",
    "ENTITY_TYPE_MEASUREMENT",
    "REL_CONNECTED_TO",
    "REL_CONTAINS",
    "REL_REFERENCES",
    "REL_CONTROLS",
    "REL_MONITORS",
    "REL_POWERED_BY",
    "REL_BELONGS_TO",
    "REL_CAUSES",
    "REL_REQUIRES",
    "REL_MEASURES",
    "REL_LOCATED_IN",
]
