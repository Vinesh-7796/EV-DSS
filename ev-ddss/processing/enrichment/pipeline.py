"""Knowledge Enrichment Pipeline — transforms CDS documents into an

engineering knowledge graph.

Pipeline stages
───────────────

    CDS Documents → Entity Extraction → Canonicalization → Alias Resolution
    → Cross-Document Linking → Relationship Discovery → Graph Enrichment
    → Knowledge Validation

Outputs
───────

    * Enriched CDS Document (with entity ContentNodes + edges)
    * Canonical Entity Index (persisted JSON)
    * Alias Dictionary (persisted JSON)
    * Enrichment Report
"""

import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.logger import logger
from processing.enrichment.extractor import EntityExtractor
from processing.enrichment.canonicalizer import Canonicalizer
from processing.enrichment.linker import CrossDocumentLinker
from processing.enrichment.discoverer import RelationshipDiscoverer
from processing.enrichment.enricher import GraphEnricher
from processing.enrichment.validator import KnowledgeValidator
from processing.enrichment.index import CanonicalEntityIndex, AliasDictionary
from processing.enrichment.models import (
    CanonicalEntity,
    EnrichmentReport,
    Entity,
    EntityRelationship,
)
from processing.models.models import Document


class KnowledgeEnrichmentPipeline:
    """End-to-end pipeline for engineering knowledge enrichment.

    Usage::

        pipeline = KnowledgeEnrichmentPipeline()
        report, enriched_doc = pipeline.enrich(document)
        print(report.summary())
    """

    def __init__(
        self,
        custom_aliases: Optional[Dict[str, str]] = None,
        index_path: Optional[Path] = None,
        alias_dict_path: Optional[Path] = None,
    ) -> None:
        self._extractor = EntityExtractor()
        self._canonicalizer = Canonicalizer(custom_aliases=custom_aliases)
        self._linker = CrossDocumentLinker()
        self._discoverer = RelationshipDiscoverer()
        self._enricher = GraphEnricher()
        self._validator = KnowledgeValidator()
        self._entity_index = CanonicalEntityIndex(path=index_path)
        self._alias_dict = AliasDictionary(path=alias_dict_path)

        # Track cross-document state
        self._canonical_entities: List[CanonicalEntity] = []

    # ── Public API ──────────────────────────────

    def enrich(
        self,
        doc: Document,
        persist_index: bool = True,
    ) -> Tuple[EnrichmentReport, Document]:
        """Run the full enrichment pipeline on a single CDS Document.

        Parameters
        ----------
        doc : Document
            A validated CDS Document from the Document Intelligence Pipeline.
        persist_index : bool
            Whether to save the canonical entity index and alias dictionary
            to disk after enrichment (default True).

        Returns
        -------
        (EnrichmentReport, Document)
            The enrichment report and the enriched Document.
        """
        logger.info("Enrichment pipeline: processing {}", doc.source)
        start = time.time()

        # Stage 1: Entity extraction
        entities = self._extractor.extract(doc.content_nodes, doc.source)

        # Stage 2: Canonicalization
        canonical = self._canonicalizer.canonicalize(entities)

        # Stage 3: Alias resolution (built into canonicalizer)

        # Stage 4: Cross-document linking
        if self._canonical_entities:
            prev_count = len(self._canonical_entities)
            self._canonical_entities = self._linker.link(
                self._canonical_entities, canonical
            )
            cross_links = len(self._canonical_entities) - prev_count
        else:
            self._canonical_entities = canonical
            cross_links = 0

        # Stage 5: Relationship discovery
        relationships = self._discoverer.discover(self._canonical_entities)

        # Stage 6: Graph enrichment
        enriched_doc = self._enricher.enrich(doc, self._canonical_entities, relationships)

        # Stage 7: Knowledge validation
        validation_issues = self._validator.validate(
            self._canonical_entities, relationships
        )

        elapsed = time.time() - start

        # Persist index and alias dictionary
        if persist_index:
            self._entity_index.save(self._canonical_entities)
            self._alias_dict.save(self._canonicalizer.alias_dictionary)

        report = EnrichmentReport(
            source_document=doc.source,
            entities_extracted=len(entities),
            entities_canonicalized=len(self._canonical_entities),
            cross_document_links=cross_links,
            relationships_discovered=len(relationships),
            validation_issues=validation_issues,
            enrichment_time_s=elapsed,
        )

        logger.info(
            "Enrichment pipeline: completed {} in {:.2f}s "
            "({} entities, {} relationships, {} issues)",
            doc.source,
            elapsed,
            len(self._canonical_entities),
            len(relationships),
            len(validation_issues),
        )

        return report, enriched_doc

    def enrich_many(
        self,
        docs: List[Document],
        persist_index: bool = True,
    ) -> List[Tuple[EnrichmentReport, Document]]:
        """Enrich multiple documents sequentially.

        Cross-document linking accumulates across all documents.
        """
        results: List[Tuple[EnrichmentReport, Document]] = []
        for doc in docs:
            report, enriched = self.enrich(doc, persist_index=False)
            results.append((report, enriched))

        if persist_index:
            self._entity_index.save(self._canonical_entities)
            self._alias_dict.save(self._canonicalizer.alias_dictionary)

        return results

    # ── Properties ──────────────────────────────

    @property
    def canonical_entities(self) -> List[CanonicalEntity]:
        return list(self._canonical_entities)

    @property
    def entity_index(self) -> CanonicalEntityIndex:
        return self._entity_index

    @property
    def alias_dictionary(self) -> AliasDictionary:
        return self._alias_dict

    def summary(self) -> str:
        """Return a human-readable summary of all enrichment runs."""
        return (
            f"Knowledge Enrichment Pipeline:\n"
            f"  Canonical entities: {len(self._canonical_entities)}\n"
            f"  Index path: {self._entity_index.path}\n"
            f"  Alias dict path: {self._alias_dict.path}"
        )
