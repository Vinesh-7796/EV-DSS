"""Hybrid Retrieval Engine — orchestrator for vector, SQL, graph, and image retrieval.

Complete profiling instrumentation added for performance analysis.
"""

import socket
import time
from typing import Any, List, Optional
from urllib.parse import urlparse

from backend.logger import logger
from retrieval.models import RetrievalMethod, RetrievalResult, StructuredContextPackage


class HybridRetrievalEngine:
    """Hybrid retrieval engine that blends results from all search strategies.

    Thread-safe and stateless per-request.  Pure orchestration layer.
    """

    def __init__(self) -> None:
        self._graph_index = None
        self._embedding_generator = None
        self._vector_disabled_until = 0.0

    # ── Initialization ───────────────────────

    def initialize(self) -> None:
        from retrieval.embeddings import EmbeddingGenerator
        from retrieval.graph_index import GraphIndex

        self._embedding_generator = EmbeddingGenerator()
        self._graph_index = GraphIndex()
        try:
            self._graph_index.load_from_index()
        except Exception as exc:
            logger.warning("Graph index initialization failed: {}", exc)
        logger.info("RetrievalEngine initialized (hybrid)")

    # ── Public API ────────────────────────────

    def retrieve(
        self,
        query: str,
        top_k_vector: int = 10,
        top_k_graph: int = 10,
        top_k_sql: int = 10,
    ) -> StructuredContextPackage:
        """Run hybrid retrieval orchestration.

        Returns a fully structured context package with metrics.
        """
        overall_start = time.time()
        logger.info("Pipeline start: query={}", query[:50])

        retrieval_start = time.time()
        vector_results = self._vector_retrieve(query, top_k=top_k_vector)
        logger.info("Vector retrieval completed in {:.3f} ms", (time.time() - retrieval_start) * 1000)

        graph_start = time.time()
        graph_results = self._graph_retrieve(query, top_k=top_k_graph)
        logger.info("Graph retrieval completed in {:.3f} ms", (time.time() - graph_start) * 1000)

        sql_start = time.time()
        sql_package = self._sql_retrieve(query, top_k=top_k_sql)
        logger.info("SQL retrieval completed in {:.3f} ms", (time.time() - sql_start) * 1000)

        hybrid_start = time.time()
        package = self._hybrid_merge(query, vector_results, graph_results, sql_package)
        logger.info("Hybrid merge completed in {:.3f} ms", (time.time() - hybrid_start) * 1000)

        total_time_ms = (time.time() - overall_start) * 1000
        logger.info("Pipeline complete in {:.3f} ms", total_time_ms)

        return package

    # ── Internal ───────────────────────────────

    def _vector_retrieve(self, query: str, top_k: int = 10) -> List[RetrievalResult]:
        from retrieval.vector_index import VectorIndex

        now = time.time()
        if now < self._vector_disabled_until:
            logger.info("Vector retrieval skipped: Qdrant unavailable cooldown active")
            return []

        idx = VectorIndex()
        try:
            if not self._qdrant_is_reachable(getattr(idx, "_url", "")):
                self._vector_disabled_until = time.time() + 60.0
                logger.warning("Vector retrieval skipped: Qdrant is not reachable")
                return []
            idx.connect()
            if self._embedding_generator is None:
                from retrieval.embeddings import EmbeddingGenerator
                self._embedding_generator = EmbeddingGenerator()
            hits = idx.search_by_text(query, self._embedding_generator.encode, top_k=top_k)
            return [self._vector_hit_to_result(hit, rank) for rank, hit in enumerate(hits, 1)]
        except Exception as exc:
            self._vector_disabled_until = time.time() + 60.0
            logger.warning("Vector retrieval failed: {}", exc)
            return []

    def _graph_retrieve(self, query: str, top_k: int = 10) -> List[RetrievalResult]:
        from retrieval.graph_index import GraphIndex

        start = time.time()
        idx = self._graph_index or GraphIndex()
        self._graph_index = idx
        try:
            graph_rows = idx.search(query, top_k=top_k)
            return [self._graph_row_to_result(row, rank) for rank, row in enumerate(graph_rows, 1)]
        except Exception as exc:
            latency_ms = (time.time() - start) * 1000
            print(f"Graph initialized: {'YES' if getattr(idx, 'is_loaded', False) else 'NO'}")
            print(f"Graph connected: {'YES' if getattr(idx, 'edge_count', 0) > 0 else 'NO'}")
            print("Method invoked: GraphIndex.search")
            print("Returned nodes: 0")
            print("Returned relationships: 0")
            print(f"Latency: {latency_ms:.3f} ms")
            logger.warning("Graph retrieval failed: {}", exc)
            return []

    def _sql_retrieve(self, query: str, top_k: int = 10) -> StructuredContextPackage:
        from retrieval.json_search import JSONStoreSearch
        store = JSONStoreSearch()
        try:
            package = store.search(query)
            package.exact_matches = package.exact_matches[:top_k]
            return package
        except Exception as exc:
            logger.warning("JSON fallback retrieval failed: {}", exc)
            return StructuredContextPackage(query=query)

    def _hybrid_merge(
        self,
        query: str,
        vector: List[RetrievalResult],
        graph: List[RetrievalResult],
        sql: StructuredContextPackage,
    ) -> StructuredContextPackage:
        package = StructuredContextPackage(
            query=query,
            semantic_context=vector,
            exact_matches=list(sql.exact_matches),
            graph_context=graph,
            image_references=list(sql.image_references),
        )
        all_results = package.all_results
        package.total_results = len(all_results)
        package.deduplicated_count = len({r.node_id for r in all_results if r.node_id})
        package.citations = [r.to_citation() for r in all_results if r.source or r.reference]
        package.methods_used = sorted({r.method.value for r in all_results if hasattr(r.method, "value")})
        package.confidence = self._calculate_confidence(all_results)
        return package

    @staticmethod
    def _vector_hit_to_result(hit: Any, rank: int) -> RetrievalResult:
        payload = hit.get("payload", {}) if isinstance(hit, dict) else {}
        return RetrievalResult(
            content=str(payload.get("text", "")),
            node_id=str(hit.get("id", "")) if isinstance(hit, dict) else "",
            node_type=str(payload.get("node_type", "")),
            source=str(payload.get("source", "")),
            document_id=str(payload.get("document_id", "")),
            score=float(hit.get("score", 0.0)) if isinstance(hit, dict) else 0.0,
            rank=rank,
            method=RetrievalMethod.VECTOR,
            metadata=payload,
            reference=payload.get("reference"),
        )

    @staticmethod
    def _graph_row_to_result(row: Any, rank: int) -> RetrievalResult:
        entity = row.get("entity") if isinstance(row, dict) else None
        hops = row.get("hops", 0) if isinstance(row, dict) else 0
        path = row.get("path", []) if isinstance(row, dict) else []
        entity_name = getattr(entity, "canonical_name", "")
        entity_type = getattr(entity, "type", "")
        content = entity_name
        if path:
            content = f"{entity_name} related via {' -> '.join(path)}"
        return RetrievalResult(
            content=content,
            node_id=getattr(entity, "id", ""),
            node_type=entity_type,
            source=", ".join(getattr(entity, "source_documents", []) or []),
            score=max(0.1, 1.0 - (0.2 * float(hops or 0))),
            rank=rank,
            method=RetrievalMethod.GRAPH,
            metadata={
                "entity_name": entity_name,
                "entity_type": entity_type,
                "hops": hops,
                "relationship_path": path,
                "aliases": getattr(entity, "aliases", []),
            },
        )

    @staticmethod
    def _calculate_confidence(results: List[RetrievalResult]) -> float:
        if not results:
            return 0.0
        return min(1.0, sum(max(0.0, min(1.0, r.score)) for r in results) / len(results))

    @staticmethod
    def _qdrant_is_reachable(url: str) -> bool:
        parsed = urlparse(url)
        host = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        if not host:
            return False
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except OSError:
            return False
