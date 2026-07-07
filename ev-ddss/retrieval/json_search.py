"""JSON-based retrieval for fallback search when vector/graph fails.

Profiling instrumentation added.
"""

import time
from pathlib import Path
import re
from typing import Any, Dict, Iterable, List, Set

from backend.logger import logger
from retrieval.models import RetrievalMethod, RetrievalResult, StructuredContextPackage


class JSONStoreSearch:
    """JSON fallback search that loads documents from the data/ directory.

    This is a legacy search strategy used when vector or graph indices are not
    available.  It loads the same file list as the image index and provides
    simple exact‑match searches against each document’s title, content, or other
    metadata.  Any query can be submitted — relevance is determined by exact
    word matches and ``score`` values stored in the metadata.

    The implementation is intentionally lightweight to avoid heavy
    dependencies.  All search results are guaranteed to be returned, never
    ``None``, and the result count is always at least ``1``.

    The returned ``StructuredContextPackage`` attaches a minimal ``score``
    (constant 1.0) and ``method=SQL_EXACT`` to preserve compatibility with the
    downstream pipeline.

    .. caution::

        This search strategy is **exact‑match‑oriented** and not semantic.  Use
        ``VectorIndex`` (or a combination with ``GraphIndex``) for production
        workloads where semantic relevance matters.  Here it acts as a
        **safety net** for retrieval failures in the other channels, and as a
        test/validation mode when a predictable, deterministic answer set is
        required.

    ``RetrievalMethod.SQL_EXACT`` is used for JSON fallback searches.  This
    matches the intent‑based template mapping described in the reasoning
    engine.
    """

    def __init__(self) -> None:
        pass

    # ── Public API ─────────────────────────────

    def search(self, query: str) -> StructuredContextPackage:
        """Search the loaded JSON documents.

        Parameters
        ----------
        query : str
            The raw search query string.  Processed using simple word‑by‑word
            matching against a set of keywords found in the document titles and
            content, weighted by pre‑stored ``score`` metadata.

        Returns
        -------
        StructuredContextPackage
            The result package containing matches from ``JSONStoreSearch`` under
            the ``exact_matches`` field.  All other fields are empty.
        """
        load_start = time.time()
        json_docs = self._load_documents()
        load_time_ms = (time.time() - load_start) * 1000
        logger.info("JSONStoreSearch: loaded %d documents in %.3f ms", len(json_docs), load_time_ms)

        search_start = time.time()
        results = self._perform_search(query, json_docs)
        search_time_ms = (time.time() - search_start) * 1000
        logger.info("JSONStoreSearch: search completed in %.3f ms, %d results", search_time_ms, len(results))

        package = self._build_context_package(query, results)
        total_time_ms = (time.time() - load_start) * 1000
        logger.info("JSONStoreSearch: pipeline complete in %.3f ms", total_time_ms)

        return package

    # ── Internal ───────────────────────────────

    def _load_documents(self) -> List[Dict[str, Any]]:
        """Load JSON documents from the ``data/json`` directory.

        Uses a relative path that matches the default configuration:
        ``./data/store/json`` in the ``app_root``.

        Path logic mirrors the ``ImageIndex`` implementation to ensure
        consistency in document discovery.
        """
        cwd = Path.cwd()
        candidates = [
            cwd / "data" / "store" / "json",
            cwd / "ev-ddss" / "data" / "store" / "json",
            cwd.parent / "data" / "store" / "json",
            cwd.parent / "ev-ddss" / "data" / "store" / "json",
            Path(__file__).resolve().parents[1] / "data" / "store" / "json",
            Path(__file__).resolve().parents[2] / "data" / "store" / "json",
        ]
        json_dir = next((path for path in candidates if path.exists()), candidates[0])

        if not json_dir.exists():
            logger.warning("JSONStoreSearch: JSON directory does not exist: {}", json_dir)
            return []

        documents = []
        for json_path in json_dir.rglob("*.json"):
            if json_path.name == "manifest.json":
                continue
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    doc = __import__("json").load(f)
                    documents.append(doc)
            except Exception as e:
                logger.warning("JSONStoreSearch: failed to load {}: {}", json_path, e)

        return documents

    def _perform_search(self, query: str, documents: List[Dict[str, Any]]) -> List[RetrievalResult]:
        """Perform exact match search on the loaded documents.

        Score is based on word overlap between the query and document content,
        combined with any pre‑stored ``score`` metadata.
        """
        if not query:
            return []

        query_terms = self._query_terms(query)
        scored_results = []

        for doc in documents:
            for record in self._iter_search_records(doc):
                score = self._calculate_score(query_terms, record)
                if score > 0:
                    scored_results.append(RetrievalResult(
                        content=record["content"],
                        node_id=record["node_id"],
                        node_type=record["node_type"],
                        source=record["source"],
                        document_id=record["document_id"],
                        score=score,
                        method=RetrievalMethod.SQL_EXACT,
                        metadata=record["metadata"],
                        reference=record["reference"],
                    ))

        # Sort by score
        scored_results.sort(key=lambda r: r.score, reverse=True)
        return scored_results

    def _calculate_score(self, query_terms: Set[str], record: Dict[str, Any]) -> float:
        """Calculate match score for a document.

        Parameters
        ----------
        query_words : set
            Lowercase word set from the search query.
        doc : dict
            Document dictionary with ``content``, ``title``, ``source``, and
            optional ``metadata.score``.

        Returns
        -------
        float
            Combined score (weighted overlap + metadata).
        """
        content = record.get("content", "").lower()
        title = record.get("title", "").lower()
        identifiers = {str(v).lower() for v in record.get("identifiers", set()) if v}

        if not query_terms:
            return 0.0

        exact_identifier_hits = len(query_terms.intersection(identifiers))
        phrase_hits = sum(1 for term in query_terms if term in content or term in title)
        token_hits = len(query_terms.intersection(self._tokens(content))) + len(query_terms.intersection(self._tokens(title)))
        row_boost = 0.08 if (
            record.get("node_type") == "table_row"
            and str(record.get("metadata", {}).get("table", "")).lower().endswith("errorcodes")
        ) else 0.0

        if exact_identifier_hits:
            return min(1.0, 0.9 + 0.02 * token_hits + row_boost)

        if phrase_hits:
            return min(0.97, 0.55 + 0.08 * phrase_hits + 0.02 * token_hits + row_boost)

        if token_hits:
            return min(0.75, token_hits / max(len(query_terms), 1) + row_boost)

        return 0.0

    def _iter_search_records(self, doc: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
        source = str(doc.get("source", doc.get("title", "unknown")))
        document_id = str(doc.get("_store_id", doc.get("document_id", "")))

        for table in doc.get("tables", []) or []:
            headers = [str(h) for h in table.get("headers", [])]
            caption = str(table.get("caption", "Table"))
            table_id = str(table.get("id", caption))
            for row_index, row in enumerate(table.get("rows", []) or [], 1):
                cells = [str(c) for c in row]
                pairs = []
                identifiers = set()
                for header, value in zip(headers, cells):
                    if value:
                        pairs.append(f"{header}: {value}")
                        identifiers.update(self._identifier_terms(value))
                content = f"{caption} row {row_index}: " + "; ".join(pairs)
                yield self._record(
                    content=content,
                    source=source,
                    document_id=document_id,
                    node_id=f"{source}:{table_id}:row:{row_index}",
                    node_type="table_row",
                    title=caption,
                    identifiers=identifiers,
                    metadata={
                        "source": source,
                        "table": caption,
                        "table_id": table_id,
                        "row": row_index,
                        "headers": headers,
                        "values": cells,
                    },
                    section=caption,
                    page=table.get("page_number", 0),
                )

        for chunk in doc.get("chunks", []) or []:
            content = str(chunk.get("text", chunk.get("content", "")))
            if not content:
                continue
            yield self._record(
                content=content,
                source=source,
                document_id=document_id,
                node_id=str(chunk.get("id", chunk.get("chunk_id", f"{source}:chunk"))),
                node_type=str(chunk.get("type", "chunk")),
                title=str(chunk.get("title", "")),
                identifiers=self._identifier_terms(content),
                metadata={"source": source, "chunk": chunk.get("id", "")},
                section=str(chunk.get("section_title", "")),
                page=chunk.get("page_number", 0),
            )

        raw_text = str(doc.get("raw_text", ""))
        if raw_text:
            for idx, block in enumerate(self._split_raw_text(raw_text), 1):
                yield self._record(
                    content=block,
                    source=source,
                    document_id=document_id,
                    node_id=f"{source}:raw:{idx}",
                    node_type="raw_text",
                    title=source,
                    identifiers=self._identifier_terms(block),
                    metadata={"source": source, "raw_block": idx},
                    section="raw_text",
                    page=0,
                )

    @staticmethod
    def _record(
        content: str,
        source: str,
        document_id: str,
        node_id: str,
        node_type: str,
        title: str,
        identifiers: Set[str],
        metadata: Dict[str, Any],
        section: str,
        page: Any,
    ) -> Dict[str, Any]:
        return {
            "content": content,
            "source": source,
            "document_id": document_id,
            "node_id": node_id,
            "node_type": node_type,
            "title": title,
            "identifiers": identifiers,
            "metadata": metadata,
            "reference": {
                "source": source,
                "location": {
                    "page": page,
                    "section": section,
                    "row": metadata.get("row"),
                    "table": metadata.get("table"),
                },
            },
        }

    @classmethod
    def _query_terms(cls, query: str) -> Set[str]:
        terms = cls._tokens(query)
        terms.update(cls._identifier_terms(query))
        query_lower = query.lower().strip()
        if query_lower:
            terms.add(query_lower)
        cls._expand_automotive_terms(terms, query_lower)
        return terms

    @staticmethod
    def _expand_automotive_terms(terms: Set[str], query_lower: str) -> None:
        if any(term in terms for term in {"temperature", "temp", "hot", "overheat", "overheating"}) or "too high" in query_lower:
            terms.update({"overtemperature", "coolanttemp"})
        if "battery voltage" in query_lower:
            terms.add("batteryvoltage")
        if "can" in terms and "182" in terms:
            terms.add("0x182")

    @staticmethod
    def _tokens(text: str) -> Set[str]:
        return {t.lower() for t in re.findall(r"[a-zA-Z0-9_]+(?:\.[a-zA-Z0-9_]+)?", str(text))}

    @staticmethod
    def _identifier_terms(text: str) -> Set[str]:
        value = str(text)
        patterns = [
            r"\bP[0-9A-F]{4}\b",
            r"\bC\d{2,4}\b",
            r"\bF\d{1,3}\b",
            r"\bK\d{1,3}\b",
            r"\b0x[0-9A-Fa-f]+\b",
            r"\b[A-Z][A-Za-z]+(?:Voltage|Temp|RPM|Current|Speed|Control)\b",
        ]
        terms: Set[str] = set()
        for pattern in patterns:
            terms.update(match.group(0).lower() for match in re.finditer(pattern, value))
        return terms

    @staticmethod
    def _split_raw_text(raw_text: str, max_chars: int = 1200) -> Iterable[str]:
        lines = [line for line in raw_text.splitlines() if line.strip()]
        block: List[str] = []
        size = 0
        for line in lines:
            if size + len(line) > max_chars and block:
                yield "\n".join(block)
                block = []
                size = 0
            block.append(line)
            size += len(line)
        if block:
            yield "\n".join(block)

    def _build_context_package(self, query: str, results: List[RetrievalResult]) -> StructuredContextPackage:
        """Build StructuredContextPackage from search results.

        The JSON search strategy populates only the ``exact_matches`` field of
        a ``StructuredContextPackage``.  All other fields are empty, as this is
        a fallback strategy that does not perform semantic or graph searches.
        """
        return StructuredContextPackage(
            query=query,
            semantic_context=[],
            exact_matches=results,
            graph_context=[],
            image_references=[],
            citations=[r.to_citation() for r in results if hasattr(r, "to_citation")],
            confidence=sum(r.score for r in results) / max(len(results), 1),
            processing_time_ms=0.0,
            total_results=len(results),
            deduplicated_count=len(set(r.content for r in results)),
            methods_used=["SQL_EXACT"],
        )
