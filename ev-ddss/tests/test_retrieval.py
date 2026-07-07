"""Tests for the Retrieval Infrastructure.

Covers content selection, chunk optimization, embedding generation,
vector indexing, graph indexing, image indexing, SQL indexing, and
the hybrid retrieval engine.
"""

from typing import Any, Dict, List

import pytest

from processing.enrichment.models import (
    CanonicalEntity,
    EntityRelationship,
    ENTITY_TYPE_ECU,
    ENTITY_TYPE_COMPONENT,
    ENTITY_TYPE_SENSOR,
    ENTITY_TYPE_ERROR_CODE,
    REL_CONTROLS,
    REL_MONITORS,
    REL_CONTAINS,
)
from processing.models.models import (
    ContentNode,
    Document,
    DocumentMetadata,
    ProcessingInfo,
    Reference,
    Statistics,
    NODE_TYPE_PARAGRAPH,
    NODE_TYPE_PROCEDURE,
    NODE_TYPE_WARNING,
    NODE_TYPE_NOTE,
    NODE_TYPE_DESCRIPTION,
    NODE_TYPE_HEADING,
    NODE_TYPE_TABLE,
    NODE_TYPE_IMAGE,
)
from retrieval.models import (
    RetrievalMethod,
    RetrievalResult,
    RetrievalQuery,
    StructuredContextPackage,
)
from retrieval.selection import (
    ContentSelector,
    is_semantic_node,
    is_excluded_node,
    count_semantic_nodes,
)
from retrieval.chunking import ChunkOptimizer
from retrieval.graph_index import GraphIndex


# ══════════════════════════════════════════════
#  Content Selection Tests
# ══════════════════════════════════════════════


class TestContentSelection:
    def test_is_semantic_node_returns_true_for_valid_types(self):
        assert is_semantic_node("paragraph") is True
        assert is_semantic_node("procedure") is True
        assert is_semantic_node("warning") is True
        assert is_semantic_node("note") is True
        assert is_semantic_node("description") is True

    def test_is_semantic_node_returns_false_for_excluded_types(self):
        assert is_semantic_node("table") is False
        assert is_semantic_node("dbc_message") is False
        assert is_semantic_node("image") is False

    def test_is_excluded_node_returns_true_for_excluded_types(self):
        assert is_excluded_node("table") is True
        assert is_excluded_node("dbc_signal") is True
        assert is_excluded_node("image") is True

    def test_is_excluded_node_returns_false_for_semantic_types(self):
        assert is_excluded_node("paragraph") is False
        assert is_excluded_node("note") is False

    def test_selector_selects_only_semantic_nodes(self):
        nodes = [
            ContentNode(id="n1", type="paragraph", content="Hello world"),
            ContentNode(id="n2", type="table", content={"headers": [], "rows": []}),
            ContentNode(id="n3", type="warning", content="Warning text"),
            ContentNode(id="n4", type="image", content={}),
            ContentNode(id="n5", type="description", content="Description text"),
        ]
        doc = Document(source="test.pdf", type="pdf", content_nodes=nodes)
        selector = ContentSelector()
        selected = selector.select(doc)
        ids = {n.id for n in selected}
        assert "n1" in ids
        assert "n2" not in ids
        assert "n3" in ids
        assert "n4" not in ids
        assert "n5" in ids

    def test_selector_handles_nested_nodes(self):
        child_para = ContentNode(id="c1", type="paragraph", content="Child text")
        parent = ContentNode(
            id="p1", type="heading", content="Section 1",
            children=[child_para],
        )
        doc = Document(source="test.pdf", type="pdf", content_nodes=[parent])
        selector = ContentSelector(include_headings=True)
        selected = selector.select(doc)
        selected_ids = {n.id for n in selected}
        assert "p1" in selected_ids
        assert "c1" in selected_ids

    def test_selector_excludes_headings_when_configured(self):
        child = ContentNode(id="c1", type="paragraph", content="Text")
        parent = ContentNode(id="p1", type="heading", content="Header", children=[child])
        doc = Document(source="test.pdf", type="pdf", content_nodes=[parent])
        selector = ContentSelector(include_headings=False)
        selected = selector.select(doc)
        selected_ids = {n.id for n in selected}
        assert "p1" not in selected_ids
        assert "c1" in selected_ids

    def test_selector_returns_empty_for_no_semantic_nodes(self):
        doc = Document(source="test.pdf", type="pdf", content_nodes=[])
        selector = ContentSelector()
        assert selector.select(doc) == []

    def test_count_semantic_nodes(self):
        nodes = [
            ContentNode(id="n1", type="paragraph"),
            ContentNode(id="n2", type="paragraph"),
            ContentNode(id="n3", type="warning"),
            ContentNode(id="n4", type="table"),
        ]
        doc = Document(source="test.pdf", type="pdf", content_nodes=nodes)
        counts = count_semantic_nodes(doc)
        assert counts.get("paragraph") == 2
        assert counts.get("warning") == 1
        assert "table" not in counts


# ══════════════════════════════════════════════
#  Chunk Optimization Tests
# ══════════════════════════════════════════════


class TestChunkOptimization:
    def test_optimize_returns_chunks_for_semantic_nodes(self):
        nodes = [
            ContentNode(id="n1", type="paragraph", content="This is a short paragraph."),
            ContentNode(id="n2", type="warning", content="Warning: check voltage first."),
        ]
        optimizer = ChunkOptimizer(chunk_size=512, chunk_overlap=0, min_chunk_tokens=0)
        chunks = optimizer.optimize(nodes, source="test.pdf", document_id="doc1")
        assert len(chunks) == 2
        assert chunks[0].chunk_id.startswith("CHUNK")
        assert "short paragraph" in chunks[0].text
        assert chunks[0].source == "test.pdf"

    def test_optimize_handles_empty_nodes(self):
        optimizer = ChunkOptimizer()
        assert optimizer.optimize([]) == []

    def test_optimize_merges_small_nodes(self):
        nodes = [
            ContentNode(id="n1", type="paragraph", content="Short."),
            ContentNode(id="n2", type="paragraph", content="Also short."),
        ]
        optimizer = ChunkOptimizer(chunk_size=512, chunk_overlap=0, min_chunk_tokens=100)
        chunks = optimizer.optimize(nodes, source="test.pdf")
        assert len(chunks) == 1
        assert "Short." in chunks[0].text
        assert "Also short." in chunks[0].text

    def test_optimize_splits_large_node(self):
        text = ". ".join(["Sentence number " + str(i) for i in range(100)])
        nodes = [ContentNode(id="n1", type="paragraph", content=text)]
        optimizer = ChunkOptimizer(chunk_size=50, chunk_overlap=0, min_chunk_tokens=0)
        chunks = optimizer.optimize(nodes, source="test.pdf")
        assert len(chunks) > 1

    def test_optimize_preserves_metadata(self):
        ref = Reference(type="pdf", location={"page": 5, "section": "3.1"})
        node = ContentNode(
            id="n1", type="paragraph", content="Important content.",
            reference=ref, metadata={"key": "val"},
        )
        optimizer = ChunkOptimizer(chunk_size=512, chunk_overlap=0, min_chunk_tokens=0)
        chunks = optimizer.optimize([node], source="test.pdf")
        assert len(chunks) == 1
        assert chunks[0].node_type == "paragraph"
        assert chunks[0].reference is not None
        assert chunks[0].metadata.get("key") == "val"

    def test_optimize_handles_dict_content(self):
        node = ContentNode(id="n1", type="paragraph", content={"text": "Dict content"})
        optimizer = ChunkOptimizer(chunk_size=512, chunk_overlap=0)
        chunks = optimizer.optimize([node], source="test.pdf")
        assert len(chunks) == 1
        assert "Dict content" in chunks[0].text

    def test_optimize_strips_whitespace(self):
        node = ContentNode(id="n1", type="paragraph", content="  Spaced text  ")
        optimizer = ChunkOptimizer(chunk_size=512, chunk_overlap=0)
        chunks = optimizer.optimize([node], source="test.pdf")
        assert chunks[0].text == "Spaced text"


# ══════════════════════════════════════════════
#  Embedding Generation Tests
# ══════════════════════════════════════════════


class TestEmbeddingGeneration:
    def test_fallback_encode_returns_deterministic_vector(self):
        from retrieval.embeddings import EmbeddingGenerator
        gen = EmbeddingGenerator(model_name="nonexistent", device="cpu")
        vec1 = gen.encode("test text")
        vec2 = gen.encode("test text")
        vec3 = gen.encode("different text")
        assert len(vec1) == 384
        assert vec1 == vec2
        assert vec1 != vec3

    def test_fallback_encode_produces_normalized_vector(self):
        from retrieval.embeddings import EmbeddingGenerator
        gen = EmbeddingGenerator(model_name="nonexistent", device="cpu")
        vec = gen.encode("test text")
        norm = sum(v * v for v in vec) ** 0.5
        assert abs(norm - 1.0) < 0.01

    def test_encode_batch_returns_matching_lengths(self):
        from retrieval.embeddings import EmbeddingGenerator
        gen = EmbeddingGenerator(model_name="nonexistent", device="cpu")
        texts = ["first", "second", "third"]
        vectors = gen.encode_batch(texts)
        assert len(vectors) == 3
        assert all(len(v) == 384 for v in vectors)

    def test_encode_batch_handles_empty_input(self):
        from retrieval.embeddings import EmbeddingGenerator
        gen = EmbeddingGenerator(model_name="nonexistent", device="cpu")
        assert gen.encode_batch([]) == []

    def test_dimension_property(self):
        from retrieval.embeddings import EmbeddingGenerator
        gen = EmbeddingGenerator(model_name="nonexistent", device="cpu")
        assert gen.dimension == 384


# ══════════════════════════════════════════════
#  Retrieval Models Tests
# ══════════════════════════════════════════════


class TestRetrievalModels:
    def test_retrieval_method_enum_values(self):
        assert RetrievalMethod.VECTOR.value == "vector"
        assert RetrievalMethod.SQL_EXACT.value == "sql_exact"
        assert RetrievalMethod.GRAPH.value == "graph"
        assert RetrievalMethod.IMAGE.value == "image"

    def test_retrieval_result_to_citation(self):
        result = RetrievalResult(
            content="test", node_id="n1", source="doc.pdf",
            score=0.95, method=RetrievalMethod.VECTOR,
            reference={"type": "pdf", "location": {"page": 5, "section": "2.1"}},
        )
        citation = result.to_citation()
        assert "doc.pdf" in citation
        assert "vector" in citation
        assert "0.95" in citation
        assert "p.5" in citation

    def test_retrieval_result_to_citation_without_reference(self):
        result = RetrievalResult(
            content="test", node_id="n1", source="doc.pdf",
            score=0.8, method=RetrievalMethod.GRAPH,
        )
        citation = result.to_citation()
        assert "doc.pdf" in citation

    def test_structured_context_package_merge(self):
        pkg1 = StructuredContextPackage(query="q1", methods_used=["vector"])
        pkg2 = StructuredContextPackage(query="q2", methods_used=["graph"])
        pkg1.merge(pkg2)
        assert "vector" in pkg1.methods_used
        assert "graph" in pkg1.methods_used

    def test_all_results_flattens_in_order(self):
        pkg = StructuredContextPackage(query="test")
        pkg.semantic_context = [
            RetrievalResult(content="a", score=0.9, method=RetrievalMethod.VECTOR),
        ]
        pkg.graph_context = [
            RetrievalResult(content="b", score=0.7, method=RetrievalMethod.GRAPH),
        ]
        all_r = pkg.all_results
        assert len(all_r) == 2
        assert all_r[0].score >= all_r[1].score


# ══════════════════════════════════════════════
#  Graph Index Tests
# ══════════════════════════════════════════════


class TestGraphIndex:
    def test_build_from_entities(self):
        entities = [
            CanonicalEntity(
                id="ecu_1", type=ENTITY_TYPE_ECU, canonical_name="BCM",
                aliases=["Body Control Module", "BCM"],
                relationships=[
                    EntityRelationship(
                        source_entity_id="ecu_1", target_entity_id="comp_1",
                        relationship_type=REL_CONTROLS, confidence=1.0,
                    ),
                ],
            ),
            CanonicalEntity(
                id="comp_1", type=ENTITY_TYPE_COMPONENT, canonical_name="Door Lock Actuator",
            ),
        ]
        index = GraphIndex()
        index.build(entities)
        assert index.is_loaded
        assert index.entity_count == 2
        assert index.edge_count >= 1

    def test_lookup_entity_by_id(self):
        entities = [
            CanonicalEntity(id="e1", type=ENTITY_TYPE_SENSOR, canonical_name="Temp Sensor"),
        ]
        index = GraphIndex()
        index.build(entities)
        found = index.lookup_entity("e1")
        assert found is not None
        assert found.canonical_name == "Temp Sensor"
        assert index.lookup_entity("nonexistent") is None

    def test_find_entity_by_name(self):
        entities = [
            CanonicalEntity(
                id="e1", type=ENTITY_TYPE_ECU, canonical_name="ECM",
                aliases=["Engine Control Module"],
            ),
        ]
        index = GraphIndex()
        index.build(entities)
        assert index.find_entity_by_name("ECM") is not None
        assert index.find_entity_by_name("Engine Control Module") is not None
        assert index.find_entity_by_name("Unknown") is None

    def test_search_entities_by_substring(self):
        entities = [
            CanonicalEntity(id="e1", type=ENTITY_TYPE_ECU, canonical_name="BCM"),
            CanonicalEntity(id="e2", type=ENTITY_TYPE_SENSOR, canonical_name="Wheel Speed Sensor"),
        ]
        index = GraphIndex()
        index.build(entities)
        results = index.search_entities("Speed")
        assert len(results) == 1
        assert results[0].id == "e2"

    def test_traverse_returns_neighbours(self):
        entities = [
            CanonicalEntity(
                id="ecm", type=ENTITY_TYPE_ECU, canonical_name="ECM",
                relationships=[
                    EntityRelationship(
                        source_entity_id="ecm", target_entity_id="sensor_1",
                        relationship_type=REL_MONITORS, confidence=1.0,
                    ),
                ],
            ),
            CanonicalEntity(id="sensor_1", type=ENTITY_TYPE_SENSOR, canonical_name="Knock Sensor"),
        ]
        index = GraphIndex()
        index.build(entities)
        neighbours = index.traverse(["ecm"], max_hops=1)
        assert len(neighbours) == 2  # self + neighbour
        hop1 = [n for n in neighbours if n["hops"] == 1]
        assert len(hop1) == 1
        assert hop1[0]["entity"].id == "sensor_1"

    def test_traverse_respects_max_hops(self):
        entities = [
            CanonicalEntity(
                id="e1", type=ENTITY_TYPE_ECU, canonical_name="ECU1",
                relationships=[EntityRelationship("e1", "e2", REL_CONTROLS, 1.0)],
            ),
            CanonicalEntity(
                id="e2", type=ENTITY_TYPE_COMPONENT, canonical_name="Comp1",
                relationships=[EntityRelationship("e2", "e3", REL_CONTAINS, 1.0)],
            ),
            CanonicalEntity(id="e3", type=ENTITY_TYPE_SENSOR, canonical_name="Sensor1"),
        ]
        index = GraphIndex()
        index.build(entities)
        one_hop = index.traverse(["e1"], max_hops=1)
        two_hop = index.traverse(["e1"], max_hops=2)
        assert len(one_hop) == 2
        assert len(two_hop) == 3

    def test_traverse_from_name(self):
        entities = [
            CanonicalEntity(
                id="ecu_1", type=ENTITY_TYPE_ECU, canonical_name="VCU",
                relationships=[EntityRelationship("ecu_1", "e_code_1", REL_MONITORS, 1.0)],
            ),
            CanonicalEntity(
                id="e_code_1", type=ENTITY_TYPE_ERROR_CODE, canonical_name="P1234",
            ),
        ]
        index = GraphIndex()
        index.build(entities)
        neighbours = index.traverse_from_name("VCU", max_hops=1)
        assert len(neighbours) >= 2

    def test_get_neighbourhood(self):
        entities = [
            CanonicalEntity(
                id="center", type=ENTITY_TYPE_ECU, canonical_name="Main ECU",
                relationships=[EntityRelationship("center", "other", REL_CONTROLS, 1.0)],
            ),
            CanonicalEntity(id="other", type=ENTITY_TYPE_COMPONENT, canonical_name="Actuator"),
        ]
        index = GraphIndex()
        index.build(entities)
        hood = index.get_neighbourhood("center", max_hops=1)
        assert hood["center"] is not None
        assert hood["center"]["name"] == "Main ECU"
        assert len(hood["neighbours"]) == 1
        assert hood["neighbours"][0]["name"] == "Actuator"
        assert hood["neighbours"][0]["hops"] == 1

    def test_build_empty_entities(self):
        index = GraphIndex()
        index.build([])
        assert index.is_loaded
        assert index.entity_count == 0


# ══════════════════════════════════════════════
#  Image Index Tests
# ══════════════════════════════════════════════


class TestImageIndex:
    def test_health_check_returns_false_when_no_dir(self, tmp_path):
        from retrieval.image_index import ImageIndex
        idx = ImageIndex(base_dir=tmp_path / "nonexistent")
        assert idx.health_check() is False

    def test_load_returns_false_when_no_dir(self, tmp_path):
        from retrieval.image_index import ImageIndex
        idx = ImageIndex(base_dir=tmp_path / "nonexistent")
        assert idx.load() is False

    def test_count_returns_zero_when_not_loaded(self, tmp_path):
        from retrieval.image_index import ImageIndex
        idx = ImageIndex(base_dir=tmp_path)
        assert idx.count == 0


# ══════════════════════════════════════════════
#  Retrieval Results Model Tests
# ══════════════════════════════════════════════


class TestRetrievalQuery:
    def test_default_values(self):
        q = RetrievalQuery(raw_text="test query")
        assert q.raw_text == "test query"
        assert q.top_k_vector == 10
        assert q.top_k_graph == 10
        assert q.top_k_sql == 10
        assert q.top_k_image == 5
        assert q.filters == {}
        assert q.entity_ids is None
        assert q.document_ids is None


class TestStructuredContextPackageEmpty:
    def test_empty_package(self):
        pkg = StructuredContextPackage(query="test")
        assert pkg.total_results == 0
        assert pkg.all_results == []
        assert pkg.confidence == 0.0
