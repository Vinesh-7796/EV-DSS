"""Tests for the Knowledge Enrichment Engine.

Covers entity extraction, canonicalization, cross-document linking,
relationship discovery, graph enrichment, validation, and the full pipeline.
"""

import json
from pathlib import Path
from typing import Any, Dict, List

import pytest

from processing.enrichment.models import (
    Entity,
    CanonicalEntity,
    EntityRelationship,
    EnrichmentReport,
    ENTITY_TYPE_ECU,
    ENTITY_TYPE_CAN_MESSAGE,
    ENTITY_TYPE_CAN_SIGNAL,
    ENTITY_TYPE_ERROR_CODE,
    ENTITY_TYPE_SENSOR,
    ENTITY_TYPE_COMPONENT,
    ENTITY_TYPE_SUBSYSTEM,
    ENTITY_TYPE_FUSE,
    ENTITY_TYPE_MEASUREMENT,
    ENTITY_TYPE_CONNECTOR,
    REL_CONTROLS,
    REL_CONTAINS,
    REL_MONITORS,
    REL_BELONGS_TO,
    REL_CONNECTED_TO,
    REL_REFERENCES,
    ALL_ENTITY_TYPES,
    ALL_RELATIONSHIP_TYPES,
)
from processing.enrichment.extractor import EntityExtractor
from processing.enrichment.canonicalizer import Canonicalizer, BUILTIN_ALIASES
from processing.enrichment.linker import CrossDocumentLinker
from processing.enrichment.discoverer import RelationshipDiscoverer
from processing.enrichment.enricher import GraphEnricher
from processing.enrichment.validator import KnowledgeValidator
from processing.enrichment.index import CanonicalEntityIndex, AliasDictionary
from processing.enrichment.pipeline import KnowledgeEnrichmentPipeline
from processing.models.models import (
    ContentNode,
    Document,
    DocumentMetadata,
    Edge,
    Reference,
    RelationshipGraph,
    NODE_TYPE_DBC_MESSAGE,
    NODE_TYPE_DBC_SIGNAL,
    NODE_TYPE_PARAGRAPH,
    NODE_TYPE_HEADING,
    NODE_TYPE_TABLE,
)


# =========================================================================
# Entity Model Tests
# =========================================================================

class TestEntityModels:
    """Verify entity dataclasses."""

    def test_entity_defaults(self) -> None:
        e = Entity()
        assert e.id == ""
        assert e.type == ""
        assert e.name == ""
        assert e.aliases == []
        assert e.confidence == 1.0

    def test_entity_full(self) -> None:
        e = Entity(
            id="ENT_abc123", type=ENTITY_TYPE_ECU, name="VCU",
            source_document="test.dbc", confidence=0.95,
        )
        assert e.id == "ENT_abc123"
        assert e.type == "ecu"
        assert e.name == "VCU"

    def test_canonical_entity(self) -> None:
        ce = CanonicalEntity(
            id="CENT_xyz", type=ENTITY_TYPE_ECU, canonical_name="Vehicle Control Unit",
            aliases=["VCU", "Veh Controller"],
        )
        assert ce.canonical_name == "Vehicle Control Unit"
        assert "VCU" in ce.aliases

    def test_entity_relationship(self) -> None:
        rel = EntityRelationship(
            source_entity_id="ENT_a", target_entity_id="ENT_b",
            relationship_type=REL_CONTROLS, confidence=0.95,
        )
        assert rel.source_entity_id == "ENT_a"
        assert rel.target_entity_id == "ENT_b"
        assert rel.relationship_type == "controls"

    def test_enrichment_report(self) -> None:
        r = EnrichmentReport(source_document="test.dbc", entities_extracted=10)
        assert r.source_document == "test.dbc"
        assert r.entities_extracted == 10
        assert "PASS" in r.summary()


# =========================================================================
# Entity Extraction Tests
# =========================================================================

class TestEntityExtractor:
    """Verify extraction of entities from ContentNodes."""

    @pytest.fixture
    def extractor(self) -> EntityExtractor:
        return EntityExtractor()

    def test_extract_dbc_message(self, extractor: EntityExtractor) -> None:
        nodes = [
            ContentNode(
                id="n1", type=NODE_TYPE_DBC_MESSAGE,
                content={"id": 385, "name": "MotorStatus", "dlc": 8, "sender": "MCU"},
                reference=Reference(type="dbc", location={"message": "MotorStatus"}),
            ),
        ]
        entities = extractor.extract(nodes, "test.dbc")
        msg_entities = [e for e in entities if e.type == ENTITY_TYPE_CAN_MESSAGE]
        assert len(msg_entities) == 1
        assert msg_entities[0].name == "MotorStatus"
        assert msg_entities[0].metadata.get("can_id") == 385

    def test_extract_dbc_signal(self, extractor: EntityExtractor) -> None:
        nodes = [
            ContentNode(
                id="n1", type=NODE_TYPE_DBC_SIGNAL,
                content={"name": "MotorRPM", "start_bit": 0, "length": 16, "unit": "rpm"},
            ),
        ]
        entities = extractor.extract(nodes, "test.dbc")
        sig_entities = [e for e in entities if e.type == ENTITY_TYPE_CAN_SIGNAL]
        assert len(sig_entities) == 1
        assert sig_entities[0].name == "MotorRPM"

    def test_extract_error_code(self, extractor: EntityExtractor) -> None:
        nodes = [
            ContentNode(
                id="n1", type=NODE_TYPE_PARAGRAPH,
                content="Error P0A00 detected in the HV system",
            ),
        ]
        entities = extractor.extract(nodes, "test.pdf")
        errs = [e for e in entities if e.type == ENTITY_TYPE_ERROR_CODE]
        assert len(errs) >= 1
        assert errs[0].name == "P0A00"

    def test_extract_measurement(self, extractor: EntityExtractor) -> None:
        nodes = [
            ContentNode(
                id="n1", type=NODE_TYPE_PARAGRAPH,
                content="The system runs at 400V and 150kW",
            ),
        ]
        entities = extractor.extract(nodes, "test.pdf")
        meas = [e for e in entities if e.type == ENTITY_TYPE_MEASUREMENT]
        assert len(meas) >= 1

    def test_extract_empty(self, extractor: EntityExtractor) -> None:
        entities = extractor.extract([], "empty.pdf")
        assert len(entities) == 0

    def test_extract_text_patterns(self, extractor: EntityExtractor) -> None:
        nodes = [
            ContentNode(
                id="n1", type=NODE_TYPE_PARAGRAPH,
                content="Check Connector X1 and Fuse F2. Relay K3 may need replacement.",
            ),
        ]
        entities = extractor.extract(nodes, "test.pdf")
        connectors = [e for e in entities if e.type == ENTITY_TYPE_CONNECTOR]
        fuses = [e for e in entities if e.type == ENTITY_TYPE_FUSE]
        assert len(connectors) >= 1
        assert len(fuses) >= 1

    def test_extract_no_duplicates(self, extractor: EntityExtractor) -> None:
        nodes = [
            ContentNode(id="n1", type=NODE_TYPE_PARAGRAPH, content="Error P0A00 found"),
            ContentNode(id="n2", type=NODE_TYPE_PARAGRAPH, content="Also error P0A00 here"),
        ]
        entities = extractor.extract(nodes, "test.pdf")
        errs = [e for e in entities if e.type == ENTITY_TYPE_ERROR_CODE]
        ids = {e.id for e in errs}
        assert len(ids) == len(errs)  # no duplicate IDs


# =========================================================================
# Canonicalization Tests
# =========================================================================

class TestCanonicalizer:
    """Verify alias resolution and entity merging."""

    @pytest.fixture
    def canonicalizer(self) -> Canonicalizer:
        return Canonicalizer()

    def test_resolve_known_alias(self, canonicalizer: Canonicalizer) -> None:
        assert canonicalizer._resolve("MCU") == "Motor Controller Unit"
        assert canonicalizer._resolve("VCU") == "Vehicle Control Unit"
        assert canonicalizer._resolve("BMS") == "Battery Management System"

    def test_resolve_unknown_name(self, canonicalizer: Canonicalizer) -> None:
        assert canonicalizer._resolve("UnknownPart") == "UnknownPart"

    def test_canonicalize_merges_aliases(self, canonicalizer: Canonicalizer) -> None:
        entities = [
            Entity(id="e1", type=ENTITY_TYPE_ECU, name="MCU"),
            Entity(id="e2", type=ENTITY_TYPE_ECU, name="Motor Controller"),
        ]
        canonical = canonicalizer.canonicalize(entities)
        assert len(canonical) == 1
        assert canonical[0].canonical_name == "Motor Controller Unit"
        assert "MCU" in canonical[0].aliases or "Motor Controller" in canonical[0].aliases

    def test_canonicalize_different_types(self, canonicalizer: Canonicalizer) -> None:
        entities = [
            Entity(id="e1", type=ENTITY_TYPE_ECU, name="MCU"),
            Entity(id="e2", type=ENTITY_TYPE_CAN_MESSAGE, name="MCU"),
        ]
        canonical = canonicalizer.canonicalize(entities)
        assert len(canonical) == 2

    def test_canonicalize_empty(self, canonicalizer: Canonicalizer) -> None:
        assert canonicalizer.canonicalize([]) == []

    def test_alias_dictionary(self, canonicalizer: Canonicalizer) -> None:
        aliases = canonicalizer.alias_dictionary
        assert "MCU" in aliases
        assert aliases["MCU"] == "Motor Controller Unit"

    def test_custom_aliases(self) -> None:
        c = Canonicalizer(custom_aliases={"XYZ": "Custom Part"})
        assert c._resolve("XYZ") == "Custom Part"
        assert c._resolve("MCU") == "Motor Controller Unit"  # built-in still works


# =========================================================================
# Cross-Document Linking Tests
# =========================================================================

class TestCrossDocumentLinker:
    """Verify cross-document entity linking."""

    @pytest.fixture
    def linker(self) -> CrossDocumentLinker:
        return CrossDocumentLinker()

    def test_link_existing(self, linker: CrossDocumentLinker) -> None:
        existing = [
            CanonicalEntity(id="c1", type=ENTITY_TYPE_ECU, canonical_name="Motor Controller Unit",
                            source_documents=["doc1.dbc"]),
        ]
        new = [
            CanonicalEntity(id="c2", type=ENTITY_TYPE_ECU, canonical_name="Motor Controller Unit",
                            source_documents=["doc2.pdf"]),
        ]
        result = linker.link(existing, new)
        assert len(result) == 1
        assert "doc1.dbc" in result[0].source_documents
        assert "doc2.pdf" in result[0].source_documents

    def test_link_new(self, linker: CrossDocumentLinker) -> None:
        existing: List[CanonicalEntity] = []
        new = [CanonicalEntity(id="c1", type=ENTITY_TYPE_ECU, canonical_name="VCU")]
        result = linker.link(existing, new)
        assert len(result) == 1
        assert result[0].id == "c1"


# =========================================================================
# Relationship Discovery Tests
# =========================================================================

class TestRelationshipDiscoverer:
    """Verify relationship discovery."""

    @pytest.fixture
    def discoverer(self) -> RelationshipDiscoverer:
        return RelationshipDiscoverer()

    def test_ecu_controls_message(self, discoverer: RelationshipDiscoverer) -> None:
        entities = [
            CanonicalEntity(id="ecu1", type=ENTITY_TYPE_ECU, canonical_name="MCU",
                            metadata={"sender": "MCU"}, source_documents=["test.dbc"]),
            CanonicalEntity(id="msg1", type=ENTITY_TYPE_CAN_MESSAGE, canonical_name="MotorStatus",
                            metadata={"sender": "MCU"}, source_documents=["test.dbc"]),
        ]
        rels = discoverer.discover(entities)
        controls = [r for r in rels if r.relationship_type == REL_CONTROLS]
        assert len(controls) >= 1

    def test_message_contains_signal(self, discoverer: RelationshipDiscoverer) -> None:
        entities = [
            CanonicalEntity(id="msg1", type=ENTITY_TYPE_CAN_MESSAGE, canonical_name="MsgA",
                            source_documents=["test.dbc"]),
            CanonicalEntity(id="sig1", type=ENTITY_TYPE_CAN_SIGNAL, canonical_name="SigX",
                            source_documents=["test.dbc"]),
        ]
        rels = discoverer.discover(entities)
        contains = [r for r in rels if r.relationship_type == REL_CONTAINS]
        assert len(contains) >= 1

    def test_discover_empty(self, discoverer: RelationshipDiscoverer) -> None:
        rels = discoverer.discover([])
        assert rels == []


# =========================================================================
# Graph Enrichment Tests
# =========================================================================

class TestGraphEnricher:
    """Verify graph enrichment."""

    @pytest.fixture
    def enricher(self) -> GraphEnricher:
        return GraphEnricher()

    def test_enrich_adds_nodes_and_edges(self, enricher: GraphEnricher) -> None:
        doc = Document(
            source="test.pdf", type="pdf",
            metadata=DocumentMetadata(filename="test.pdf"),
        )
        entities = [
            CanonicalEntity(id="c_ecu1", type=ENTITY_TYPE_ECU, canonical_name="VCU"),
        ]
        rels = [
            EntityRelationship(
                source_entity_id="c_ecu1", target_entity_id="c_msg1",
                relationship_type=REL_CONTROLS,
            ),
        ]
        enriched = enricher.enrich(doc, entities, rels)
        assert enricher.stats["nodes_added"] >= 1
        # Check the node was added to content_nodes
        assert any("enriched_c_ecu1" in (c.id if hasattr(c, "id") else c.get("id", ""))
                   for c in enriched.content_nodes)


# =========================================================================
# Knowledge Validation Tests
# =========================================================================

class TestKnowledgeValidator:
    """Verify knowledge validation."""

    @pytest.fixture
    def validator(self) -> KnowledgeValidator:
        return KnowledgeValidator()

    def test_valid_knowledge(self, validator: KnowledgeValidator) -> None:
        entities = [
            CanonicalEntity(id="e1", type=ENTITY_TYPE_ECU, canonical_name="VCU"),
        ]
        rels = [
            EntityRelationship(source_entity_id="e1", target_entity_id="e2",
                               relationship_type=REL_CONTROLS),
        ]
        issues = validator.validate(entities, rels)
        # e2 not found -> broken reference
        broken = [i for i in issues if "broken" in i.lower()]
        assert len(broken) >= 1

    def test_orphan_detection(self, validator: KnowledgeValidator) -> None:
        entities = [
            CanonicalEntity(id="e1", type=ENTITY_TYPE_ECU, canonical_name="VCU"),
        ]
        issues = validator.validate(entities, [])
        orphan = [i for i in issues if "orphan" in i.lower()]
        assert len(orphan) >= 1

    def test_duplicate_detection(self, validator: KnowledgeValidator) -> None:
        entities = [
            CanonicalEntity(id="e1", type=ENTITY_TYPE_ECU, canonical_name="VCU"),
            CanonicalEntity(id="e2", type=ENTITY_TYPE_ECU, canonical_name="VCU"),
        ]
        issues = validator.validate(entities, [])
        dup = [i for i in issues if "duplicate" in i.lower()]
        assert len(dup) >= 1

    def test_missing_name(self, validator: KnowledgeValidator) -> None:
        entities = [
            CanonicalEntity(id="e1", type=ENTITY_TYPE_ECU, canonical_name=""),
        ]
        issues = validator.validate(entities, [])
        missing = [i for i in issues if "empty canonical" in i.lower()]
        assert len(missing) >= 1

    def test_unknown_relationship_type(self, validator: KnowledgeValidator) -> None:
        entities = [CanonicalEntity(id="e1", type=ENTITY_TYPE_ECU, canonical_name="VCU")]
        rels = [EntityRelationship(source_entity_id="e1", target_entity_id="e2",
                                   relationship_type="fake_type")]
        issues = validator.validate(entities, rels)
        unknown = [i for i in issues if "unknown" in i.lower()]
        assert len(unknown) >= 1


# =========================================================================
# Index Persistence Tests
# =========================================================================

class TestCanonicalEntityIndex:
    """Verify CanonicalEntityIndex persistence."""

    @pytest.fixture
    def index(self, tmp_path: Path) -> CanonicalEntityIndex:
        return CanonicalEntityIndex(path=tmp_path / "test_index.json")

    def test_save_and_load(self, index: CanonicalEntityIndex) -> None:
        entities = [
            CanonicalEntity(id="c1", type=ENTITY_TYPE_ECU, canonical_name="VCU",
                            aliases=["Vehicle Control Unit"]),
        ]
        index.save(entities)
        loaded = index.load()
        assert len(loaded) == 1
        assert loaded[0].canonical_name == "VCU"
        assert "Vehicle Control Unit" in loaded[0].aliases

    def test_lookup(self, index: CanonicalEntityIndex) -> None:
        entities = [CanonicalEntity(id="c1", type=ENTITY_TYPE_ECU, canonical_name="VCU")]
        index.save(entities)
        result = index.lookup("c1")
        assert result is not None
        assert result["canonical_name"] == "VCU"

    def test_lookup_missing(self, index: CanonicalEntityIndex) -> None:
        assert index.lookup("nonexistent") is None

    def test_search(self, index: CanonicalEntityIndex) -> None:
        entities = [CanonicalEntity(id="c1", type=ENTITY_TYPE_ECU, canonical_name="Motor Controller Unit")]
        index.save(entities)
        results = index.search("motor")
        assert len(results) >= 1


class TestAliasDictionary:
    """Verify AliasDictionary persistence."""

    @pytest.fixture
    def ad(self, tmp_path: Path) -> AliasDictionary:
        return AliasDictionary(path=tmp_path / "test_aliases.json")

    def test_save_and_load(self, ad: AliasDictionary) -> None:
        aliases = {"MCU": "Motor Controller Unit", "VCU": "Vehicle Control Unit"}
        ad.save(aliases)
        loaded = ad.load()
        assert loaded["MCU"] == "Motor Controller Unit"
        assert loaded["VCU"] == "Vehicle Control Unit"

    def test_resolve(self, ad: AliasDictionary) -> None:
        ad.save({"MCU": "Motor Controller Unit"})
        assert ad.resolve("MCU") == "Motor Controller Unit"
        assert ad.resolve("Unknown") == "Unknown"


# =========================================================================
# Knowledge Enrichment Pipeline - End-to-End Tests
# =========================================================================

class TestKnowledgeEnrichmentPipeline:
    """Verify the full enrichment pipeline."""

    @pytest.fixture
    def pipeline(self, tmp_path: Path) -> KnowledgeEnrichmentPipeline:
        return KnowledgeEnrichmentPipeline(
            index_path=tmp_path / "e2e_index.json",
            alias_dict_path=tmp_path / "e2e_aliases.json",
        )

    def test_enrich_dbc_document(self, pipeline: KnowledgeEnrichmentPipeline) -> None:
        doc = Document(
            source="test.dbc", type="dbc",
            metadata=DocumentMetadata(filename="test.dbc"),
            content_nodes=[
                ContentNode(
                    id="n1", type=NODE_TYPE_DBC_MESSAGE,
                    content={"id": 100, "name": "TestMsg", "dlc": 8, "sender": "MCU"},
                    reference=Reference(type="dbc", location={"message": "TestMsg"}),
                    children=[
                        ContentNode(
                            id="n2", type=NODE_TYPE_DBC_SIGNAL,
                            content={"name": "Sig1", "start_bit": 0, "length": 8, "unit": "V"},
                            parent_id="n1",
                        ),
                    ],
                ),
            ],
        )
        report, enriched = pipeline.enrich(doc)
        assert report.entities_extracted >= 2  # message + signal
        assert report.relationships_discovered >= 1
        assert enriched.content_nodes is not None

    def test_enrich_multiple_documents(self, tmp_path: Path) -> None:
        pipeline = KnowledgeEnrichmentPipeline(
            index_path=tmp_path / "multi_index.json",
            alias_dict_path=tmp_path / "multi_aliases.json",
        )
        doc1 = Document(
            source="doc1.dbc", type="dbc",
            metadata=DocumentMetadata(filename="doc1.dbc"),
            content_nodes=[
                ContentNode(id="n1", type=NODE_TYPE_DBC_MESSAGE,
                            content={"id": 100, "name": "MsgA", "sender": "ECU1"}),
            ],
        )
        doc2 = Document(
            source="doc2.pdf", type="pdf",
            metadata=DocumentMetadata(filename="doc2.pdf"),
            content_nodes=[
                ContentNode(id="n2", type=NODE_TYPE_PARAGRAPH,
                            content="ECU1 controls the motor"),
            ],
        )
        reports = pipeline.enrich_many([doc1, doc2])
        assert len(reports) == 2
        for r, _ in reports:
            assert r.entities_extracted >= 0
        assert pipeline.canonical_entities is not None

    def test_enrich_empty_document(self, pipeline: KnowledgeEnrichmentPipeline) -> None:
        doc = Document(source="empty.pdf", type="pdf", metadata=DocumentMetadata(filename="empty.pdf"))
        report, enriched = pipeline.enrich(doc)
        assert report.entities_extracted == 0
        assert enriched.content_nodes == []

    def test_pipeline_summary(self, pipeline: KnowledgeEnrichmentPipeline) -> None:
        summary = pipeline.summary()
        assert "Enrichment Pipeline" in summary or "entities" in summary


# =========================================================================
# Constants Tests
# =========================================================================

class TestConstants:
    """Verify entity and relationship type constants."""

    def test_all_entity_types_defined(self) -> None:
        assert len(ALL_ENTITY_TYPES) >= 10  # at least 10 entity types

    def test_all_relationship_types_defined(self) -> None:
        assert len(ALL_RELATIONSHIP_TYPES) >= 10  # at least 10 relationship types

    def test_builtin_aliases_have_entries(self) -> None:
        assert len(BUILTIN_ALIASES) >= 20  # at least 20 built-in aliases
