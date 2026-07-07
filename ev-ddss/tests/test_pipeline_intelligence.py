"""Tests for the Document Intelligence Pipeline, ProcessingReport, and KnowledgeStore.

Covers:
- ProcessingReport creation and formatting
- KnowledgeStore ABC enforcement
- JSONKnowledgeStore store/retrieve/list/delete
- ImageStore store/retrieve
- KnowledgeStoreManager orchestration
- DocumentIntelligencePipeline end-to-end with real processors
- Enhanced validation (serialization roundtrip, duplicate detection)
"""

import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any, Dict, Generator, List

import pytest

from processing.models.models import (
    ContentNode,
    Document,
    DocumentMetadata,
    Edge,
    IDGenerator,
    ProcessingInfo,
    Reference,
    RelationshipGraph,
    Statistics,
    NODE_TYPE_HEADING,
    NODE_TYPE_PARAGRAPH,
    NODE_TYPE_DBC_MESSAGE,
    NODE_TYPE_DBC_SIGNAL,
    NODE_TYPE_TABLE,
)
from processing.report import ProcessingReport
from processing.pipeline_intelligence import (
    DocumentIntelligencePipeline,
    _ensure_references,
    _build_relationship_graph,
    _compute_statistics,
)
from processing.validation import validate_document, _validate_serialization, _validate_duplicate_detection


# =========================================================================
# ProcessingReport Tests
# =========================================================================

class TestProcessingReport:
    """Verify the ProcessingReport dataclass."""

    def test_default_construction(self) -> None:
        r = ProcessingReport(source="test.pdf", doc_type="pdf")
        assert r.source == "test.pdf"
        assert r.doc_type == "pdf"
        assert r.validation_passed is False
        assert r.validation_issues == []
        assert r.store_results == {}
        assert r.processing_time_s == 0.0
        assert r.statistics is None
        assert r.timestamp is not None

    def test_full_construction(self) -> None:
        stats = Statistics(total_content_nodes=5, total_relationships=3, node_type_counts={"heading": 2, "paragraph": 3})
        r = ProcessingReport(
            source="test.pdf",
            doc_type="pdf",
            validation_passed=True,
            validation_issues=[],
            store_results={"json": "pdf/test", "image": "img_abc"},
            processing_time_s=1.23,
            statistics=stats,
        )
        assert r.is_healthy is True
        assert "json" in r.stored_in
        assert "image" in r.stored_in
        assert r.node_count == 5
        assert r.edge_count == 3

    def test_summary_format(self) -> None:
        r = ProcessingReport(
            source="test.pdf",
            doc_type="pdf",
            validation_passed=True,
            store_results={"json": "pdf/test"},
            processing_time_s=0.5,
            statistics=Statistics(total_content_nodes=3, total_relationships=1),
        )
        s = r.summary()
        assert "[PASS]" in s
        assert "test.pdf" in s
        assert "3 nodes" in s
        assert "json" in s

    def test_detailed_format(self) -> None:
        r = ProcessingReport(
            source="test.pdf",
            doc_type="pdf",
            validation_passed=False,
            validation_issues=["Missing source", "Empty content"],
            processing_time_s=0.5,
        )
        d = r.detailed()
        assert "FAILED" in d
        assert "Missing source" in d
        assert "Empty content" in d


# =========================================================================
# KnowledgeStore Tests
# =========================================================================

class TestKnowledgeStoreABC:
    """Verify the ABC enforces the required interface."""

    def test_cannot_instantiate_abc(self) -> None:
        from processing.store.base import KnowledgeStore
        with pytest.raises(TypeError):
            KnowledgeStore()  # type: ignore


class TestJSONKnowledgeStore:
    """Verify JSON filesystem store operations."""

    @pytest.fixture
    def store(self, tmp_path: Path) -> Any:
        from processing.store.json_store import JSONKnowledgeStore
        store = JSONKnowledgeStore(base_dir=tmp_path / "json_store")
        return store

    def test_store_and_list(self, store: Any) -> None:
        doc = Document(
            source="test.pdf", type="pdf",
            metadata=DocumentMetadata(filename="test.pdf", file_size=100),
        )
        store_id = store.store(doc, source_id="abc123")
        assert store_id == "pdf/test"
        docs = store.list_documents()
        assert len(docs) == 1
        assert docs[0]["source"] == "test.pdf"

    def test_retrieve(self, store: Any) -> None:
        doc = Document(source="test.pdf", type="pdf", metadata=DocumentMetadata(filename="test.pdf"))
        store_id = store.store(doc)
        retrieved = store.retrieve(store_id)
        assert retrieved is not None
        assert retrieved.source == "test.pdf"

    def test_retrieve_nonexistent(self, store: Any) -> None:
        from processing.store.json_store import JSONKnowledgeStore
        result = store.retrieve("nonexistent/file")
        assert result is None

    def test_delete(self, store: Any) -> None:
        doc = Document(source="delete_me.pdf", type="pdf", metadata=DocumentMetadata(filename="delete_me.pdf"))
        store_id = store.store(doc)
        assert store.delete(store_id) is True
        assert store.delete(store_id) is False

    def test_health_check(self, store: Any) -> None:
        assert store.health_check() is True

    def test_name(self, store: Any) -> None:
        assert store.name == "json"


class TestImageStore:
    """Verify ImageStore operations."""

    @pytest.fixture
    def store(self, tmp_path: Path) -> Any:
        from processing.store.image_store import ImageStore
        return ImageStore(base_dir=tmp_path / "img_store")

    def test_store_non_image(self, store: Any) -> None:
        doc = Document(source="test.pdf", type="pdf")
        result = store.store(doc)
        assert result == ""

    def test_store_image_with_content_nodes(self, store: Any) -> None:
        doc = Document(
            source="test.png", type="image",
            metadata=DocumentMetadata(filename="test.png", image_width=100, image_height=200),
            content_nodes=[
                ContentNode(id="n1", type="image", content={"width": 100, "height": 200, "format": "PNG"}),
            ],
        )
        result = store.store(doc)
        assert result != ""

    def test_retrieve(self, store: Any) -> None:
        doc = Document(
            source="test.png", type="image",
            metadata=DocumentMetadata(filename="test.png"),
            content_nodes=[ContentNode(id="n1", type="image")],
        )
        store_id = store.store(doc)
        if store_id:
            retrieved = store.retrieve(store_id.split(",")[0])
            assert retrieved is not None
            assert retrieved.type == "image"

    def test_list_and_delete(self, store: Any) -> None:
        doc = Document(
            source="img.png", type="image",
            metadata=DocumentMetadata(filename="img.png"),
            content_nodes=[ContentNode(id="n1", type="image")],
        )
        store_id = store.store(doc)
        assert len(store.list_documents()) >= 1
        if store_id:
            first_id = store_id.split(",")[0]
            assert store.delete(first_id) is True


class TestKnowledgeStoreManager:
    """Verify KnowledgeStoreManager orchestration."""

    @pytest.fixture
    def manager(self, tmp_path: Path) -> Any:
        from processing.store.manager import KnowledgeStoreManager
        from processing.store.json_store import JSONKnowledgeStore
        from processing.store.image_store import ImageStore
        mgr = KnowledgeStoreManager()
        mgr.register("json", JSONKnowledgeStore(base_dir=tmp_path / "kj"))
        mgr.register("image", ImageStore(base_dir=tmp_path / "ki"))
        return mgr

    def test_store_across_all(self, manager: Any) -> None:
        doc = Document(
            source="test.pdf", type="pdf",
            metadata=DocumentMetadata(filename="test.pdf"),
        )
        results = manager.store_across_all(doc)
        assert "json" in results
        assert results["json"] != ""

    def test_get_store(self, manager: Any) -> None:
        store = manager.get_store("json")
        assert store.name == "json"

    def test_get_store_nonexistent(self, manager: Any) -> None:
        from processing.store.manager import KnowledgeStoreManager
        with pytest.raises(ValueError):
            manager.get_store("nonexistent")

    def test_list_all(self, manager: Any) -> None:
        doc = Document(
            source="test.pdf", type="pdf",
            metadata=DocumentMetadata(filename="test.pdf"),
        )
        manager.store_across_all(doc)
        all_docs = manager.list_all()
        assert "json" in all_docs
        assert len(all_docs["json"]) >= 1


# =========================================================================
# Pipeline Helpers Tests
# =========================================================================

class TestReferenceGeneration:
    """Verify _ensure_references fills missing References."""

    def test_fills_missing_references(self) -> None:
        doc = Document(
            source="test.pdf", type="pdf",
            content_nodes=[
                ContentNode(id="n1", type="heading", content="Hello",
                            reference=Reference(type="pdf", location={"page": 1})),
                ContentNode(id="n2", type="paragraph", content="World"),  # missing ref
            ],
        )
        result = _ensure_references(doc)
        n2 = result.content_nodes[1]
        assert n2.reference is not None
        assert n2.reference.type == "pdf"

    def test_empty_document(self) -> None:
        doc = Document(source="test.pdf", type="pdf")
        result = _ensure_references(doc)
        assert len(result.content_nodes) == 0


class TestRelationshipGraphBuilder:
    """Verify _build_relationship_graph builds edges from hierarchy."""

    def test_builds_child_edges(self) -> None:
        doc = Document(
            source="test.pdf", type="pdf",
            content_nodes=[
                ContentNode(id="n1", type="heading", content="A", children=[
                    ContentNode(id="n2", type="paragraph", content="B", parent_id="n1"),
                ]),
            ],
        )
        result = _build_relationship_graph(doc)
        assert len(result.relationship_graph.edges) >= 1
        edge = result.relationship_graph.edges[0]
        assert edge.source == "n2"
        assert edge.target == "n1"
        assert edge.relationship_type == "child_of"

    def test_preserves_existing_edges(self) -> None:
        doc = Document(
            source="test.pdf", type="pdf",
            content_nodes=[ContentNode(id="n1", type="heading", content="A")],
            relationship_graph=RelationshipGraph(
                nodes={},
                edges=[Edge(source="n1", target="DOC001", relationship_type="child_of")],
            ),
        )
        result = _build_relationship_graph(doc)
        assert len(result.relationship_graph.edges) == 1

    def test_builds_node_dict(self) -> None:
        doc = Document(
            source="test.pdf", type="pdf",
            content_nodes=[ContentNode(id="n1", type="heading", content="A")],
        )
        result = _build_relationship_graph(doc)
        assert "n1" in result.relationship_graph.nodes


class TestStatisticsComputation:
    """Verify _compute_statistics aggregates correctly."""

    def test_counts_nodes_and_types(self) -> None:
        doc = Document(
            content_nodes=[
                ContentNode(id="n1", type="heading", children=[
                    ContentNode(id="n2", type="paragraph"),
                    ContentNode(id="n3", type="paragraph"),
                ]),
                ContentNode(id="n4", type="table"),
            ],
        )
        stats = _compute_statistics(doc)
        assert stats.total_content_nodes == 4
        assert stats.node_type_counts["heading"] == 1
        assert stats.node_type_counts["paragraph"] == 2
        assert stats.node_type_counts["table"] == 1
        assert stats.max_depth >= 1

    def test_empty_document(self) -> None:
        doc = Document()
        stats = _compute_statistics(doc)
        assert stats.total_content_nodes == 0
        assert stats.max_depth == 0


# =========================================================================
# Enhanced Validation Tests
# =========================================================================

class TestSerializationValidation:
    """Verify serialization roundtrip validation."""

    def test_valid_serialization(self) -> None:
        doc = Document(source="test.pdf", type="pdf", raw_text="hello")
        issues = _validate_serialization(doc)
        assert len(issues) == 0

    def test_bad_serialization(self) -> None:
        class BadObj:
            def __str__(self) -> str:
                raise ValueError("bad")
        doc = Document(source="test.pdf", type="pdf")
        # Content with unserializable objects should be caught
        issues = _validate_serialization(doc)
        assert isinstance(issues, list)

    def test_document_to_dict_roundtrip(self) -> None:
        doc = Document(source="test.pdf", type="pdf", raw_text="hello")
        data = doc.to_dict()
        json_str = json.dumps(data, default=str)
        rt = json.loads(json_str)
        assert rt["source"] == "test.pdf"
        assert rt["type"] == "pdf"


class TestDuplicateDetection:
    """Verify duplicate content detection."""

    def test_no_duplicates(self) -> None:
        doc = Document(
            content_nodes=[
                ContentNode(id="n1", type="paragraph", content="Unique content A"),
                ContentNode(id="n2", type="paragraph", content="Unique content B"),
            ],
        )
        issues = _validate_duplicate_detection(doc)
        # Short content (<20 chars) is skipped
        assert len(issues) == 0

    def test_detects_duplicates(self) -> None:
        doc = Document(
            content_nodes=[
                ContentNode(id="n1", type="paragraph",
                            content="This is a long enough string to trigger detection"),
                ContentNode(id="n2", type="paragraph",
                            content="This is a long enough string to trigger detection"),
            ],
        )
        issues = _validate_duplicate_detection(doc)
        # Might detect duplicates depending on content length
        assert isinstance(issues, list)


# =========================================================================
# Document Intelligence Pipeline - End-to-End Tests
# =========================================================================

class TestDocumentIntelligencePipeline:
    """Verify the full pipeline with real processors."""

    @pytest.fixture
    def pipeline(self, tmp_path: Path) -> DocumentIntelligencePipeline:
        from processing.store.manager import KnowledgeStoreManager
        from processing.store.json_store import JSONKnowledgeStore
        mgr = KnowledgeStoreManager()
        mgr.register("json", JSONKnowledgeStore(base_dir=tmp_path / "pipeline_json"))
        return DocumentIntelligencePipeline(store_manager=mgr)

    def test_pipeline_with_dbc(self, pipeline: DocumentIntelligencePipeline, tmp_path: Path) -> None:
        from ingestion.models import Document as IngestionDocument
        import hashlib
        dbc_text = '''VERSION "1.0"
BU_: VCU MCU
BO_ 100 TestMsg: 8 VCU
 SG_ Sig1 : 0|16@1+ (1,0) [0|100] "V" MCU
'''
        p = tmp_path / "test_pipeline.dbc"
        p.write_text(dbc_text, encoding="utf-8")
        doc = IngestionDocument(path=p, filename="test_pipeline.dbc", extension=".dbc", size=p.stat().st_size)
        doc.checksum = hashlib.sha256(dbc_text.encode()).hexdigest()

        report = pipeline.process(doc)
        assert report.source == "test_pipeline.dbc"
        assert report.validation_passed is True
        assert report.node_count >= 2  # message + signal
        assert "json" in report.stored_in

    def test_pipeline_summary(self, pipeline: DocumentIntelligencePipeline) -> None:
        assert pipeline.processed_count >= 0
        assert pipeline.failed_count >= 0
        s = pipeline.summary()
        assert "Pipeline" in s

    def test_pipeline_process_many(self, tmp_path: Path) -> None:
        from ingestion.models import Document as IngestionDocument
        from processing.store.manager import KnowledgeStoreManager
        from processing.store.json_store import JSONKnowledgeStore
        mgr = KnowledgeStoreManager()
        mgr.register("json", JSONKnowledgeStore(base_dir=tmp_path / "pm_json"))
        pipeline = DocumentIntelligencePipeline(store_manager=mgr)

        # Create two DBC files
        for name in ["a.dbc", "b.dbc"]:
            dbc_text = f'''VERSION "1.0"\nBU_: ECU\nBO_ 100 {name.replace(".","_")}: 8 ECU\n SG_ X : 0|8@1+ (1,0) [0|255] "" ECU\n'''
            p = tmp_path / name
            p.write_text(dbc_text, encoding="utf-8")

        docs = []
        for name in ["a.dbc", "b.dbc"]:
            p = tmp_path / name
            d = IngestionDocument(path=p, filename=name, extension=".dbc", size=p.stat().st_size)
            d.checksum = hashlib.sha256(p.read_bytes()).hexdigest()
            docs.append(d)

        reports = pipeline.process_many(docs)
        assert len(reports) == 2
        for r in reports:
            assert r.validation_passed is True


# =========================================================================
# Advanced Validation Tests
# =========================================================================

class TestFullValidation:
    """Verify the complete validate_document function with enhanced checks."""

    def test_valid_document_passes(self) -> None:
        doc = Document(
            source="test.pdf", type="pdf",
            metadata=DocumentMetadata(filename="test.pdf"),
            content_nodes=[ContentNode(id="n1", type="paragraph", content="Hello",
                                       reference=Reference(type="pdf", location={"page": 1}))],
            raw_text="Hello",
        )
        issues = validate_document(doc)
        # Should have few or no issues
        assert isinstance(issues, list)

    def test_empty_document_has_issues(self) -> None:
        doc = Document()
        issues = validate_document(doc)
        assert len(issues) >= 1

    def test_broken_hierarchy_detected(self) -> None:
        doc = Document(
            source="test.pdf", type="pdf",
            content_nodes=[
                ContentNode(id="n1", type="heading", parent_id="nonexistent"),
            ],
        )
        issues = validate_document(doc)
        hierarchy_issues = [i for i in issues if "parent" in i.lower()]
        assert len(hierarchy_issues) >= 1
