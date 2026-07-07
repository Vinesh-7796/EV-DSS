"""Retrieval Pipeline — builds all indexes from enriched CDS Documents.

Pipeline stages
───────────────

    Enriched CDS → Content Selection → Chunk Optimization →
    Embedding Generation → Vector Indexing → Graph Indexing →
    SQL Indexing → Image Indexing

This pipeline is designed to be run after the Document Intelligence
Pipeline and Knowledge Enrichment have completed.
"""

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.logger import logger
from processing.enrichment.index import CanonicalEntityIndex
from processing.enrichment.models import CanonicalEntity
from processing.models.models import Document
from retrieval.chunking import ChunkOptimizer
from retrieval.embeddings import EmbeddingGenerator
from retrieval.graph_index import GraphIndex
from retrieval.image_index import ImageIndex
from retrieval.selection import ContentSelector
from retrieval.sql_index import SQLIndex
from retrieval.vector_index import VectorIndex


@dataclass
class RetrievalPipelineReport:
    """Summary of a retrieval pipeline run."""

    documents_processed: int = 0
    total_chunks: int = 0
    vectors_indexed: int = 0
    graph_entities: int = 0
    graph_edges: int = 0
    images_indexed: int = 0
    sql_records_available: int = 0
    processing_time_s: float = 0.0
    errors: List[str] = field(default_factory=list)


class RetrievalPipeline:
    """Builds all retrieval indexes from enriched CDS Documents.

    Usage::

        pipeline = RetrievalPipeline()
        report = pipeline.build(documents)
        print(report)
    """

    def __init__(
        self,
        content_selector: Optional[ContentSelector] = None,
        chunk_optimizer: Optional[ChunkOptimizer] = None,
        embedding_generator: Optional[EmbeddingGenerator] = None,
        vector_index: Optional[VectorIndex] = None,
        sql_index: Optional[SQLIndex] = None,
        graph_index: Optional[GraphIndex] = None,
        image_index: Optional[ImageIndex] = None,
        entity_index: Optional[CanonicalEntityIndex] = None,
    ) -> None:
        self._content_selector = content_selector or ContentSelector()
        self._chunk_optimizer = chunk_optimizer or ChunkOptimizer()
        self._embedding_generator = embedding_generator or EmbeddingGenerator()
        self._vector_index = vector_index or VectorIndex()
        self._sql_index = sql_index or SQLIndex()
        self._graph_index = graph_index or GraphIndex(entity_index=entity_index)
        self._image_index = image_index or ImageIndex()
        self._entity_index = entity_index or CanonicalEntityIndex()

    # ── Public API ──────────────────────────────

    def build(
        self,
        documents: Optional[List[Document]] = None,
    ) -> RetrievalPipelineReport:
        """Build all indexes.

        If *documents* is provided, processes each document through
        content selection → chunking → embedding → vector upsert.
        Graph and image indexes are loaded from their respective
        persistent stores.

        Parameters
        ----------
        documents : List[Document] or None
            Enriched CDS Documents to index. If None, only loads
            the graph and image indexes from existing data.

        Returns
        -------
        RetrievalPipelineReport
            Summary of what was indexed.
        """
        start = time.time()
        report = RetrievalPipelineReport()

        # Stage 1: Warm up embedding model
        logger.info("RetrievalPipeline: warming up embedding model...")
        try:
            self._embedding_generator.warmup()
        except Exception as exc:
            report.errors.append(f"Embedding model warmup failed: {exc}")

        # Stage 2: Connect to vector index
        logger.info("RetrievalPipeline: connecting to vector index...")
        try:
            self._vector_index.connect()
            self._vector_index.ensure_collection()
        except Exception as exc:
            report.errors.append(f"Vector index connect failed: {exc}")

        # Stage 3: Process documents (content selection → chunking → embedding → vector upsert)
        if documents:
            logger.info("RetrievalPipeline: processing {} documents...", len(documents))
            for doc in documents:
                try:
                    self._process_document(doc, report)
                except Exception as exc:
                    report.errors.append(f"Document '{doc.source}' failed: {exc}")

        # Stage 4: Load graph index from persistent entity index
        logger.info("RetrievalPipeline: loading graph index...")
        try:
            loaded = self._graph_index.load_from_index()
            if loaded:
                report.graph_entities = self._graph_index.entity_count
                report.graph_edges = self._graph_index.edge_count
        except Exception as exc:
            report.errors.append(f"Graph index load failed: {exc}")

        # Stage 5: Load image index
        logger.info("RetrievalPipeline: loading image index...")
        try:
            self._image_index.load()
            report.images_indexed = self._image_index.count
        except Exception as exc:
            report.errors.append(f"Image index load failed: {exc}")

        # Stage 6: Check SQL index availability
        try:
            if self._sql_index.health_check():
                docs = self._sql_index.list_documents()
                report.sql_records_available = len(docs)
        except Exception:
            pass

        report.processing_time_s = round(time.time() - start, 2)
        logger.info("RetrievalPipeline: build complete ({})", report)
        return report

    # ── Single document processing ──────────────

    def _process_document(
        self,
        doc: Document,
        report: RetrievalPipelineReport,
    ) -> None:
        # Content selection
        semantic_nodes = self._content_selector.select(doc)
        if not semantic_nodes:
            logger.debug("RetrievalPipeline: no semantic nodes in '{}'", doc.source)
            return

        # Chunk optimization
        chunks = self._chunk_optimizer.optimize(
            semantic_nodes,
            source=doc.source,
            document_id=getattr(doc, "id", ""),
        )
        if not chunks:
            return

        report.documents_processed += 1
        report.total_chunks += len(chunks)

        # Embedding + vector upsert
        indexed = self._embed_and_upsert(chunks)
        report.vectors_indexed += indexed

    def _embed_and_upsert(self, chunks: List[Any]) -> int:
        texts = [c.text for c in chunks]
        vectors = self._embedding_generator.encode_batch(texts)

        points = []
        for chunk, vector in zip(chunks, vectors):
            payload = {
                "node_id": chunk.chunk_id,
                "node_type": chunk.node_type,
                "text": chunk.text,
                "source": chunk.source,
                "document_id": chunk.document_id,
                "section_title": chunk.section_title,
                "page_number": chunk.page_number,
                "parent_id": chunk.parent_id or "",
                "original_node_ids": chunk.original_node_ids,
                "reference": chunk.reference,
            }
            points.append((chunk.chunk_id, vector, payload))

        return self._vector_index.upsert(points)

    # ── Report ──────────────────────────────────

    def summary(self) -> str:
        return (
            "Retrieval Pipeline Summary\n"
        )
