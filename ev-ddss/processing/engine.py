"""Generic Processing Engine for the Canonical Document Schema.

The engine orchestrates document processing:

1. Receive an IngestionDocument
2. Select the appropriate processor by file extension
3. Execute the processor (which returns a ProcessingResult and saves JSON)
4. Load the saved Document, validate CDS, and return

Processors implement only extraction logic; the engine handles routing,
validation, and reporting.
"""

import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from backend.logger import logger
from ingestion.base.parser import BaseParser
from ingestion.models import Document as IngestionDocument, ProcessingResult, ProcessingStatus
from processing.models.models import Document
from processing.utils.io import ensure_output_dir, load_processed_document
from processing.validation import assert_valid, ValidationError


class ProcessingEngine:
    """Document-agnostic processing engine.

    The engine is completely generic — it does not know about PDF, Excel,
    DBC, or Image specifics.  Adding a new document type only requires
    implementing a new ``BaseParser`` subclass and registering it.
    """

    def __init__(self) -> None:
        self._processors: Dict[str, BaseParser] = {}

    # ── Registration ───────────────────────────

    def register(self, processor: BaseParser) -> None:
        """Register a processor for its supported extensions."""
        for ext in processor.supported_extensions:
            self._processors[ext] = processor
        logger.debug("Registered {} for {}", processor.parser_name, processor.supported_extensions)

    def register_defaults(self) -> None:
        """Register all built-in processors."""
        from processing.pdf.processor import PDFProcessor
        from processing.excel.processor import ExcelProcessor
        from processing.dbc.processor import DBCProcessor
        from processing.image.processor import ImageProcessor
        self.register(PDFProcessor())
        self.register(ExcelProcessor())
        self.register(DBCProcessor())
        self.register(ImageProcessor())

    # ── Selection ──────────────────────────────

    def select_processor(self, ingestion_doc: IngestionDocument) -> BaseParser:
        """Return the registered processor for the document's extension."""
        ext = ingestion_doc.extension.lower()
        if ext in self._processors:
            return self._processors[ext]
        raise ValueError(
            f"No processor registered for extension '{ext}'. "
            f"Supported: {list(self._processors.keys())}"
        )

    # ── Execution ──────────────────────────────

    def process(self, ingestion_doc: IngestionDocument) -> Document:
        """Run the full processing pipeline for a single document.

        Steps:

        1. Select processor
        2. Execute processor (saves JSON to ``data/processed/<type>/``)
        3. Load saved Document and validate CDS
        4. Return the validated Document
        """
        logger.info("Engine processing: {}", ingestion_doc.filename)
        processor = self.select_processor(ingestion_doc)
        result = processor.parse(ingestion_doc)

        if result.processed < 1:
            logger.warning("Engine: processor returned no successful documents")
            return Document(
                source=ingestion_doc.filename,
                type=Path(ingestion_doc.filename).suffix.lstrip("."),
            )

        # Load the saved JSON back as a Document dict
        stem = Path(ingestion_doc.filename).stem
        doc_type = Path(ingestion_doc.filename).suffix.lstrip(".").lower()
        saved_path = ensure_output_dir(doc_type) / f"{stem}.json"

        if not saved_path.exists():
            logger.warning("Engine: expected output not found at {}", saved_path)
            return Document(
                source=ingestion_doc.filename,
                type=doc_type,
            )

        raw = load_processed_document(saved_path)
        doc = dict_to_document(raw)

        # Validate CDS
        try:
            assert_valid(doc)
            logger.info("Engine: CDS validation passed for {}", ingestion_doc.filename)
        except ValidationError as exc:
            logger.warning("Engine: CDS validation issues for {}: {}", ingestion_doc.filename, exc)

        return doc

    def process_many(self, docs: List[IngestionDocument]) -> List[Document]:
        """Process multiple documents sequentially."""
        return [self.process(d) for d in docs]

    # ── Reporting ──────────────────────────────

    def generate_report(self, doc: Document) -> str:
        """Produce a human-readable processing report."""
        lines = [
            f"Document: {doc.source}",
            f"Type: {doc.type}",
            f"Content nodes: {doc.statistics.total_content_nodes}",
            f"Relationships: {doc.statistics.total_relationships}",
        ]
        if doc.statistics.node_type_counts:
            lines.append("Node type breakdown:")
            for ntype, count in sorted(doc.statistics.node_type_counts.items()):
                lines.append(f"  {ntype}: {count}")
        if doc.processing_info.processor_name:
            lines.append(f"Processor: {doc.processing_info.processor_name}")
            lines.append(f"Processing time: {doc.processing_info.processing_time_s:.2f}s")
            lines.append(f"Schema version: {doc.processing_info.schema_version}")
        return "\n".join(lines)

    @property
    def supported_extensions(self) -> List[str]:
        """All extensions supported by registered processors."""
        return list(self._processors.keys())


# ──────────────────────────────────────────────
#  Internal helpers
# ──────────────────────────────────────────────


def dict_to_document(raw: Dict[str, Any]) -> Document:
    """Convert a dictionary (from JSON) back into a Document.

    Handles the basic fields; CDS fields are reconstructed as plain dicts
    since the full dataclass deserialization is complex.  Callers that
    need full CDS objects should use the processors directly.
    """
    from processing.models.models import (
        DocumentMetadata,
    )

    meta_raw = raw.get("metadata", {})
    meta = DocumentMetadata(
        filename=meta_raw.get("filename", ""),
        file_size=meta_raw.get("file_size", 0),
        checksum=meta_raw.get("checksum", ""),
        page_count=meta_raw.get("page_count", 0),
        sheet_count=meta_raw.get("sheet_count", 0),
        message_count=meta_raw.get("message_count", 0),
        image_width=meta_raw.get("image_width", 0),
        image_height=meta_raw.get("image_height", 0),
        image_format=meta_raw.get("image_format", ""),
        processed_at=meta_raw.get("processed_at", ""),
        processing_time_s=meta_raw.get("processing_time_s", 0.0),
    )

    doc = Document(
        source=raw.get("source", ""),
        type=raw.get("type", ""),
        metadata=meta,
        raw_text=raw.get("raw_text", ""),
    )
    doc.sections = raw.get("sections", [])
    doc.tables = raw.get("tables", [])
    doc.chunks = raw.get("chunks", [])
    doc.images = raw.get("images", [])

    # CDS fields (kept as-is from JSON dict)
    doc.content_nodes = raw.get("content_nodes", [])
    doc.relationship_graph = raw.get("relationship_graph", {})
    doc.processing_info = raw.get("processing_info", {})
    doc.statistics = raw.get("statistics", {})
    return doc


# Backward-compat alias
_dict_to_document = dict_to_document
