"""Data models for the ingestion framework.

Defines the core domain objects: Document, ProcessingStatus, ProcessingResult.
"""

import hashlib
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class ProcessingStatus(str, Enum):
    """Tracks the lifecycle state of a document through the ingestion pipeline."""

    DISCOVERED = "discovered"
    VALIDATED = "validated"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

    def __str__(self) -> str:
        return self.value


class Document:
    """Represents a single file discovered in the ingestion data source.

    Carries all metadata, processing state, and result information
    through the ingestion pipeline. No file contents are stored here.
    """

    def __init__(
        self,
        path: Path,
        checksum: Optional[str] = None,
        size: Optional[int] = None,
        extension: Optional[str] = None,
        filename: Optional[str] = None,
        status: ProcessingStatus = ProcessingStatus.DISCOVERED,
        metadata: Optional[Dict[str, Any]] = None,
        warnings: Optional[List[str]] = None,
        errors: Optional[List[str]] = None,
    ) -> None:
        self._id: str = ""
        self.path: Path = path
        self.filename: str = filename or path.name
        self.extension: str = extension or path.suffix.lower()
        self.size: int = size or 0
        self.checksum: str = checksum or ""
        self.status: ProcessingStatus = status
        self.metadata: Dict[str, Any] = metadata or {}
        self.warnings: List[str] = warnings or []
        self.errors: List[str] = errors or []
        self.created_at: datetime = datetime.now()
        self.updated_at: datetime = datetime.now()
        self.parsed_at: Optional[datetime] = None

    @property
    def id(self) -> str:
        """Unique identifier derived from the checksum for deduplication."""
        if not self._id:
            self._id = self.checksum or self._compute_id()
        return self._id

    def _compute_id(self) -> str:
        """Fallback ID computation using path."""
        raw = str(self.path.resolve()).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()[:16]

    def mark(self, status: ProcessingStatus) -> None:
        """Advance the document to a new processing status."""
        self.status = status
        self.updated_at = datetime.now()
        if status == ProcessingStatus.COMPLETED:
            self.parsed_at = datetime.now()

    def add_warning(self, message: str) -> None:
        """Append a non-fatal warning message."""
        self.warnings.append(message)
        self.updated_at = datetime.now()

    def add_error(self, message: str) -> None:
        """Append a fatal error message."""
        self.errors.append(message)
        self.updated_at = datetime.now()

    @property
    def is_valid(self) -> bool:
        """Whether the document passed validation."""
        return self.status in (ProcessingStatus.VALIDATED, ProcessingStatus.COMPLETED)

    @property
    def has_failed(self) -> bool:
        """Whether the document encountered a fatal error."""
        return self.status == ProcessingStatus.FAILED

    def __repr__(self) -> str:
        return f"Document({self.filename}, {self.status})"


class ProcessingResult:
    """Aggregated result of processing one or more documents.

    Produced by the pipeline after execution completes.
    """

    def __init__(
        self,
        documents: Optional[List[Document]] = None,
        parser_name: Optional[str] = None,
        duration_s: float = 0.0,
    ) -> None:
        self.documents: List[Document] = documents or []
        self.parser_name: Optional[str] = parser_name
        self.duration_s: float = duration_s
        self.timestamp: datetime = datetime.now()

    @property
    def discovered(self) -> int:
        return len(self.documents)

    @property
    def processed(self) -> int:
        return sum(1 for d in self.documents if d.status == ProcessingStatus.COMPLETED)

    @property
    def failed(self) -> int:
        return sum(1 for d in self.documents if d.status == ProcessingStatus.FAILED)

    @property
    def skipped(self) -> int:
        return sum(1 for d in self.documents if d.status == ProcessingStatus.SKIPPED)

    @property
    def validated(self) -> int:
        return sum(1 for d in self.documents if d.is_valid)

    def merge(self, other: "ProcessingResult") -> "ProcessingResult":
        """Combine two results into a single aggregate."""
        self.documents.extend(other.documents)
        self.duration_s += other.duration_s
        return self

    def __repr__(self) -> str:
        return (
            f"ProcessingResult("
            f"discovered={self.discovered}, "
            f"processed={self.processed}, "
            f"failed={self.failed}, "
            f"skipped={self.skipped})"
        )
