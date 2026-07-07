"""SQLAlchemy ORM models for EV-DDSS.

Defines the database schema for persisting CDS Documents as normalised
SQL records.  Used by the ``PostgreSQLKnowledgeStore``.
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, Float, Integer, String, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from database.base import Base

try:
    from sqlalchemy.dialects.postgresql import UUID, JSONB

    HAS_UUID = True
except ImportError:
    HAS_UUID = False


class ProcessedDocument(Base):
    """Top-level document table — one row per processed CDS Document."""

    __tablename__ = "processed_documents"

    id = Column(UUID(as_uuid=True) if HAS_UUID else String(36), primary_key=True, default=uuid.uuid4)
    source = Column(String(500), nullable=False, index=True)
    type = Column(String(50), nullable=False, index=True)
    filename = Column(String(255))
    file_size = Column(Integer, default=0)
    checksum = Column(String(128), index=True)
    raw_text = Column(Text, nullable=True)
    content_node_count = Column(Integer, default=0)
    edge_count = Column(Integer, default=0)
    processing_info = Column(JSONB if HAS_UUID else Text, nullable=True)
    statistics = Column(JSONB if HAS_UUID else Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    def __repr__(self) -> str:
        return f"ProcessedDocument(id={self.id}, source={self.source}, type={self.type})"


class ContentNode(Base):
    """Each ContentNode in a CDS Document becomes a row in this table."""

    __tablename__ = "content_nodes"

    id = Column(String(255), primary_key=True)
    document_id = Column(
        UUID(as_uuid=True) if HAS_UUID else String(36),
        ForeignKey("processed_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type = Column(String(50), nullable=False, index=True)
    content = Column(JSONB if HAS_UUID else Text, nullable=True)
    reference = Column(JSONB if HAS_UUID else Text, nullable=True)
    parent_id = Column(String(255), nullable=True, index=True)
    metadata_ = Column("metadata", JSONB if HAS_UUID else Text, nullable=True)

    def __repr__(self) -> str:
        return f"ContentNode(id={self.id}, type={self.type})"


class Edge(Base):
    """Relationship edges between ContentNodes."""

    __tablename__ = "edges"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(
        UUID(as_uuid=True) if HAS_UUID else String(36),
        ForeignKey("processed_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source = Column(String(255), nullable=False, index=True)
    target = Column(String(255), nullable=False, index=True)
    relationship_type = Column(String(100), nullable=False)
    confidence = Column(Float, default=1.0)
    metadata_ = Column("metadata", JSONB if HAS_UUID else Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("document_id", "source", "target", "relationship_type", name="uq_edge"),
    )

    def __repr__(self) -> str:
        return f"Edge({self.source} -[{self.relationship_type}]-> {self.target})"
