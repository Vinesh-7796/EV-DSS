"""Document Processing Engine for EV-DDSS.

Transforms engineering documents (PDF, Excel, DBC, Image) into
a standardized internal representation (JSON) suitable for later
stages including entity resolution, knowledge base construction,
embedding generation, and hybrid retrieval.

The Canonical Document Schema (CDS) provides a unified ContentNode-based
representation across all document types.  The Generic Processing Engine
orchestrates processor selection, execution, CDS validation, and
serialization.

The Document Intelligence Pipeline chains processors, validation,
reference generation, relationship graph construction, and persistence
through the KnowledgeStore abstraction.

The Knowledge Enrichment Engine transforms CDS documents into an
engineering knowledge graph by resolving entities, canonicalizing
terminology, and linking information across documents.
"""

from processing.pdf.processor import PDFProcessor
from processing.excel.processor import ExcelProcessor
from processing.dbc.processor import DBCProcessor
from processing.image.processor import ImageProcessor
from processing.engine import ProcessingEngine, dict_to_document
from processing.validation import (
    validate_document,
    assert_valid,
    ValidationError,
)
from processing.report import ProcessingReport
from processing.pipeline_intelligence import DocumentIntelligencePipeline

# Store exports
from processing.store.base import KnowledgeStore
from processing.store.json_store import JSONKnowledgeStore
from processing.store.sql_store import PostgreSQLKnowledgeStore
from processing.store.image_store import ImageStore
from processing.store.manager import KnowledgeStoreManager

# Enrichment exports
from processing.enrichment.models import (
    Entity,
    CanonicalEntity,
    EntityRelationship,
    EnrichmentReport,
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
    # Processors
    "PDFProcessor",
    "ExcelProcessor",
    "DBCProcessor",
    "ImageProcessor",
    # Engine
    "ProcessingEngine",
    "dict_to_document",
    # Validation
    "validate_document",
    "assert_valid",
    "ValidationError",
    # Pipeline
    "DocumentIntelligencePipeline",
    "ProcessingReport",
    # Store
    "KnowledgeStore",
    "JSONKnowledgeStore",
    "PostgreSQLKnowledgeStore",
    "ImageStore",
    "KnowledgeStoreManager",
    # Enrichment
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
]
