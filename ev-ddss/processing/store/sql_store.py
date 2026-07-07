"""PostgreSQL implementation of the KnowledgeStore interface.

Persists CDS Documents as fully normalised SQL records across three
tables: ``processed_documents``, ``content_nodes``, and ``edges``.

The store degrades gracefully when PostgreSQL is unavailable — callers
should check ``health_check()`` before storing.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.logger import logger
from processing.models.models import Document
from processing.store.base import KnowledgeStore

try:
    from sqlalchemy import Column, Float, Integer, String, Text, DateTime, ForeignKey, JSON
    from sqlalchemy.dialects.postgresql import UUID, JSONB
    from sqlalchemy.orm import relationship
    from database.base import Base
    from database.connection import DatabaseManager, get_database

    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False


# ──────────────────────────────────────────────
#  ORM models  (defined here for cohesion)
# ──────────────────────────────────────────────


class ProcessedDocumentRecord(Base if HAS_SQLALCHEMY else object):
    """ORM model for the ``processed_documents`` table."""
    if HAS_SQLALCHEMY:
        __tablename__ = "processed_documents"

        id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
        source = Column(String(500), nullable=False)
        type = Column(String(50), nullable=False)
        filename = Column(String(255))
        file_size = Column(Integer)
        checksum = Column(String(128))
        raw_text = Column(Text)
        content_node_count = Column(Integer, default=0)
        edge_count = Column(Integer, default=0)
        processing_info = Column(JSONB)
        statistics = Column(JSONB)
        created_at = Column(DateTime, default=datetime.now)


class ContentNodeRecord(Base if HAS_SQLALCHEMY else object):
    """ORM model for the ``content_nodes`` table."""
    if HAS_SQLALCHEMY:
        __tablename__ = "content_nodes"

        id = Column(String(255), primary_key=True)
        document_id = Column(UUID(as_uuid=True), ForeignKey("processed_documents.id", ondelete="CASCADE"))
        type = Column(String(50), nullable=False)
        content = Column(JSONB)
        reference = Column(JSONB)
        parent_id = Column(String(255), nullable=True)
        metadata_ = Column("metadata", JSONB)


class EdgeRecord(Base if HAS_SQLALCHEMY else object):
    """ORM model for the ``edges`` table."""
    if HAS_SQLALCHEMY:
        __tablename__ = "edges"

        id = Column(Integer, primary_key=True, autoincrement=True)
        document_id = Column(UUID(as_uuid=True), ForeignKey("processed_documents.id", ondelete="CASCADE"))
        source = Column(String(255))
        target = Column(String(255))
        relationship_type = Column(String(100), nullable=False)
        confidence = Column(Float, default=1.0)
        metadata_ = Column("metadata", JSONB)


# ──────────────────────────────────────────────
#  Store implementation
# ──────────────────────────────────────────────


class PostgreSQLKnowledgeStore(KnowledgeStore):
    """Persists CDS Documents as normalised SQL records.

    Requires a running PostgreSQL instance.  Check ``health_check()``
    before calling ``store()``.
    """

    def __init__(self, db_manager: Optional[Any] = None) -> None:
        if not HAS_SQLALCHEMY:
            raise ImportError("SQLAlchemy is required for PostgreSQLKnowledgeStore")

        self._db = db_manager or get_database()
        self._tables_created = False
        self._doc_counter = 0

    # ── KnowledgeStore interface ─────────────────

    def store(self, document: Document, source_id: str = "") -> str:
        if not self._db.is_connected:
            logger.warning("PostgreSQLKnowledgeStore: not connected, skipping store")
            return ""

        if not self._tables_created:
            self._ensure_tables()

        doc_id = uuid.uuid4()
        store_id = str(doc_id)

        with self._db.get_session() as session:
            doc_record = ProcessedDocumentRecord(
                id=doc_id,
                source=document.source,
                type=document.type,
                filename=document.metadata.filename,
                file_size=document.metadata.file_size,
                checksum=document.metadata.checksum,
                raw_text=document.raw_text[:100000] if document.raw_text else None,
                content_node_count=document.statistics.total_content_nodes,
                edge_count=document.statistics.total_relationships,
                processing_info=self._to_jsonb(document.processing_info),
                statistics=self._to_jsonb(document.statistics),
                created_at=datetime.now(),
            )
            session.add(doc_record)

            self._store_content_nodes(session, doc_id, document.content_nodes)
            self._store_edges(session, doc_id, document.relationship_graph)

        self._doc_counter += 1
        logger.info("PostgreSQLKnowledgeStore: stored {} (id={})", document.source, store_id)
        return store_id

    def retrieve(self, store_id: str) -> Optional[Document]:
        if not self._db.is_connected:
            return None
        try:
            doc_uuid = uuid.UUID(store_id)
        except ValueError:
            return None

        if not self._tables_created:
            self._ensure_tables()

        with self._db.get_session() as session:
            record = session.query(ProcessedDocumentRecord).filter_by(id=doc_uuid).first()
            if record is None:
                return None

            from processing.models.models import Document, DocumentMetadata, ProcessingInfo, Statistics
            doc = Document(
                source=record.source,
                type=record.type,
                metadata=DocumentMetadata(
                    filename=record.filename or "",
                    file_size=record.file_size or 0,
                    checksum=record.checksum or "",
                ),
                raw_text=record.raw_text or "",
            )
            # Restore statistics
            if record.statistics:
                doc.statistics.total_content_nodes = record.statistics.get("total_content_nodes", 0)
                doc.statistics.total_relationships = record.statistics.get("total_relationships", 0)
                doc.statistics.node_type_counts = record.statistics.get("node_type_counts", {})

            # Restore content nodes
            cn_records = session.query(ContentNodeRecord).filter_by(document_id=doc_uuid).all()
            cn_map: Dict[str, Any] = {}
            for cnr in cn_records:
                from processing.models.models import ContentNode, Reference
                ref = None
                if cnr.reference:
                    ref = Reference(type=cnr.reference.get("type", ""), location=cnr.reference.get("location", {}))
                node = ContentNode(
                    id=cnr.id,
                    type=cnr.type,
                    content=cnr.content,
                    reference=ref,
                    parent_id=cnr.parent_id,
                    metadata=cnr.metadata_ or {},
                )
                cn_map[cnr.id] = node

            # Rebuild hierarchy
            root_nodes = []
            for node in cn_map.values():
                if node.parent_id and node.parent_id in cn_map:
                    parent = cn_map[node.parent_id]
                    parent.children.append(node)
                else:
                    root_nodes.append(node)
            doc.content_nodes = root_nodes

            return doc

    def list_documents(self) -> List[Dict[str, Any]]:
        if not self._db.is_connected:
            return []
        if not self._tables_created:
            self._ensure_tables()
        with self._db.get_session() as session:
            records = session.query(ProcessedDocumentRecord).all()
            return [
                {
                    "store_id": str(r.id),
                    "source": r.source,
                    "type": r.type,
                    "filename": r.filename,
                    "file_size": r.file_size,
                    "checksum": r.checksum,
                    "content_node_count": r.content_node_count,
                    "edge_count": r.edge_count,
                    "stored_at": r.created_at.isoformat() if r.created_at else "",
                }
                for r in records
            ]

    def delete(self, store_id: str) -> bool:
        if not self._db.is_connected:
            return False
        try:
            doc_uuid = uuid.UUID(store_id)
        except ValueError:
            return False
        if not self._tables_created:
            self._ensure_tables()
        with self._db.get_session() as session:
            record = session.query(ProcessedDocumentRecord).filter_by(id=doc_uuid).first()
            if record is None:
                return False
            session.delete(record)
            return True

    def health_check(self) -> bool:
        if not self._db.is_connected:
            return False
        try:
            with self._db.get_session() as session:
                from sqlalchemy import text
                session.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    @property
    def name(self) -> str:
        return "postgresql"

    # ── Internal helpers ────────────────────────

    def _ensure_tables(self) -> None:
        if HAS_SQLALCHEMY and self._db.is_connected:
            try:
                Base.metadata.create_all(
                    self._db._engine,
                    tables=[
                        ProcessedDocumentRecord.__table__,
                        ContentNodeRecord.__table__,
                        EdgeRecord.__table__,
                    ],
                )
                self._tables_created = True
            except Exception as exc:
                logger.warning("PostgreSQLKnowledgeStore: table creation failed: {}", exc)

    def _store_content_nodes(
        self, session: Any, doc_id: uuid.UUID, nodes: List[Any], parent_id: Optional[str] = None
    ) -> None:
        for node in nodes:
            record = ContentNodeRecord(
                id=node.id,
                document_id=doc_id,
                type=node.type,
                content=self._to_jsonb(node.content),
                reference=self._to_jsonb(node.reference),
                parent_id=node.parent_id,
                metadata_=self._to_jsonb(node.metadata),
            )
            session.add(record)
            self._store_content_nodes(session, doc_id, node.children, node.id)

    def _store_edges(self, session: Any, doc_id: uuid.UUID, graph: Any) -> None:
        edges = graph.edges if hasattr(graph, "edges") else (graph.get("edges", []) if isinstance(graph, dict) else [])
        for edge in edges:
            record = EdgeRecord(
                document_id=doc_id,
                source=edge.source if hasattr(edge, "source") else edge.get("source", ""),
                target=edge.target if hasattr(edge, "target") else edge.get("target", ""),
                relationship_type=edge.relationship_type
                if hasattr(edge, "relationship_type") else edge.get("relationship_type", ""),
                confidence=edge.confidence if hasattr(edge, "confidence") else edge.get("confidence", 1.0),
                metadata_=self._to_jsonb(
                    edge.metadata if hasattr(edge, "metadata") else edge.get("metadata", {})
                ),
            )
            session.add(record)

    @staticmethod
    def _to_jsonb(obj: Any) -> Any:
        """Convert a dataclass or arbitrary object to a JSON-compatible dict."""
        if obj is None:
            return None
        if hasattr(obj, "__dataclass_fields__"):
            result = {}
            for f in obj.__dataclass_fields__:
                val = getattr(obj, f)
                if val is not None:
                    result[f] = PostgreSQLKnowledgeStore._to_jsonb(val)
            return result
        if isinstance(obj, (str, int, float, bool)):
            return obj
        if isinstance(obj, (list, tuple)):
            return [PostgreSQLKnowledgeStore._to_jsonb(v) for v in obj]
        if isinstance(obj, dict):
            return {k: PostgreSQLKnowledgeStore._to_jsonb(v) for k, v in obj.items()}
        return str(obj)
