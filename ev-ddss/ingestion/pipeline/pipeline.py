"""Core ingestion pipeline orchestrator.

Coordinates the full workflow for every discovered document:

    Discover -> Validate -> Extract Metadata -> Lookup Parser ->
    Execute Parser -> Produce Result
"""

import time
from pathlib import Path
from typing import List, Optional

from backend.logger import logger
from ingestion.discovery.scanner import DocumentScanner
from ingestion.metadata.extractor import MetadataExtractor
from ingestion.models import Document, ProcessingResult, ProcessingStatus
from ingestion.registry.registry import ParserRegistry
from ingestion.reporting.reporter import ProcessingReporter
from ingestion.validation.validator import DocumentValidator


class IngestionPipeline:
    """Orchestrates the end-to-end document ingestion workflow.

    Usage:
        pipeline = IngestionPipeline()
        pipeline.register_parsers()
        result = pipeline.run("data/raw")
        print(pipeline.report(result))
    """

    def __init__(self) -> None:
        self.scanner: DocumentScanner = DocumentScanner(Path("."))
        self.validator: DocumentValidator = DocumentValidator()
        self.metadata_extractor: MetadataExtractor = MetadataExtractor()
        self.registry: ParserRegistry = ParserRegistry()
        self.reporter: ProcessingReporter = ProcessingReporter()

    def register_default_parsers(self) -> None:
        """Register all built-in parsers with the registry.

        Extensions are mapped to parser classes automatically via the
        registry's register() method — no if/else chains.

        Phase 2: replaces stub parsers with real document processors.
        """
        from processing.pdf.processor import PDFProcessor
        from processing.excel.processor import ExcelProcessor
        from processing.dbc.processor import DBCProcessor
        from processing.image.processor import ImageProcessor

        self.registry.register(PDFProcessor)
        self.registry.register(ExcelProcessor)
        self.registry.register(DBCProcessor)
        self.registry.register(ImageProcessor)

        logger.info(
            "Registered {} parser(s): {}",
            len(self.registry.parser_names),
            ", ".join(self.registry.parser_names),
        )

    def run(
        self,
        root_path: Path,
        include_extensions: Optional[List[str]] = None,
    ) -> ProcessingResult:
        """Execute the full ingestion pipeline.

        Args:
            root_path: Root directory to scan recursively.
            include_extensions: Optional filter to only process specific
                extensions. If None, all registered extensions are used.

        Returns:
            An aggregated ProcessingResult with all document outcomes.
        """
        start_time = time.time()
        logger.info("Ingestion pipeline started: root={}", root_path)

        # 1. Discover documents
        effective_extensions = include_extensions or self.registry.supported_extensions
        self.scanner = DocumentScanner(
            root_path=root_path,
            include_extensions=effective_extensions,
        )
        self.validator = DocumentValidator(
            supported_extensions=effective_extensions,
        )
        documents: List[Document] = self.scanner.scan()

        if not documents:
            logger.warning("No documents found in {}", root_path)
            return ProcessingResult(duration_s=time.time() - start_time)

        logger.info("Discovered {} document(s)", len(documents))

        # 2-5. Process each document
        for doc in documents:
            self._process_document(doc)

        # 6. Aggregate results
        result = ProcessingResult(
            documents=documents,
            duration_s=time.time() - start_time,
        )

        logger.info("Ingestion pipeline finished in {:.2f}s", result.duration_s)
        return result

    def _process_document(self, doc: Document) -> None:
        """Run the full workflow for a single document.

        Steps: Validate -> Extract Metadata -> Lookup Parser -> Execute.
        """
        # 2. Validate
        is_valid = self.validator.validate(doc)
        if not is_valid:
            logger.warning("Validation failed for {}: {}", doc.filename, doc.errors)
            return

        # 3. Extract metadata (filesystem only, no content read)
        self.metadata_extractor.extract(doc)

        # Re-check validation now that checksum is known
        if doc.status != ProcessingStatus.VALIDATED:
            return

        # 4. Lookup parser
        parser = self.registry.lookup(doc.extension)
        if parser is None:
            doc.add_error(f"No parser registered for extension '{doc.extension}'")
            doc.mark(ProcessingStatus.SKIPPED)
            logger.warning("No parser for {} (extension: {})", doc.filename, doc.extension)
            return

        # 5. Execute parser
        doc.mark(ProcessingStatus.RUNNING)
        try:
            parser.validate(doc)
            result = parser.parse(doc)
            parser.normalize(doc)
            _ = result  # Result aggregated at pipeline level
        except Exception as exc:
            doc.add_error(f"Parser exception: {exc}")
            doc.mark(ProcessingStatus.FAILED)
            logger.error("Parser failed for {}: {}", doc.filename, exc)
        finally:
            parser.cleanup(doc)

    def report(self, result: ProcessingResult) -> str:
        """Generate a human-readable processing summary.

        Args:
            result: The result from a previous run() call.

        Returns:
            Formatted summary string.
        """
        return self.reporter.report(result)
