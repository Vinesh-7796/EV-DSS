"""Tests for the Phase 1 ingestion framework.

Covers models, discovery, validation, metadata extraction, registry,
stub parsers, and the full pipeline.
"""

import hashlib
from pathlib import Path
from typing import Generator

import pytest

from ingestion.models import Document, ProcessingResult, ProcessingStatus
from ingestion.discovery.scanner import DocumentScanner
from ingestion.validation.validator import DocumentValidator
from ingestion.metadata.extractor import MetadataExtractor
from ingestion.registry.registry import ParserRegistry
from ingestion.base.parser import BaseParser
from ingestion.parsers.pdf.parser import PDFParser as StubPDFParser
from ingestion.parsers.excel.parser import ExcelParser as StubExcelParser
from ingestion.parsers.image.parser import ImageParser as StubImageParser
from ingestion.parsers.dbc.parser import DBCParser as StubDBCParser
from ingestion.pipeline.pipeline import IngestionPipeline


# =========================================================================
# Fixtures
# =========================================================================

@pytest.fixture
def temp_dir(tmp_path: Path) -> Generator[Path, None, None]:
    """Provide a temporary directory with test files."""
    # Create a few test files
    (tmp_path / "test.pdf").write_text("dummy pdf content")
    (tmp_path / "test.xlsx").write_text("dummy excel content")
    (tmp_path / "test.png").write_text("dummy image content")
    (tmp_path / "test.dbc").write_text("dummy dbc content")
    (tmp_path / "unsupported.xyz").write_text("dummy unknown")
    (tmp_path / "subdir").mkdir()
    (tmp_path / "subdir" / "nested.pdf").write_text("nested pdf")
    yield tmp_path


@pytest.fixture
def empty_file(tmp_path: Path) -> Path:
    """Provide an empty file."""
    p = tmp_path / "empty.pdf"
    p.write_text("")
    return p


# =========================================================================
# Document Model
# =========================================================================

class TestDocument:
    """Verify the Document data model."""

    def test_initial_status(self, tmp_path: Path) -> None:
        doc = Document(path=tmp_path / "test.pdf")
        assert doc.status == ProcessingStatus.DISCOVERED
        assert doc.warnings == []
        assert doc.errors == []

    def test_mark_status(self, tmp_path: Path) -> None:
        doc = Document(path=tmp_path / "test.pdf")
        doc.mark(ProcessingStatus.VALIDATED)
        assert doc.status == ProcessingStatus.VALIDATED
        assert doc.is_valid

    def test_mark_failed(self, tmp_path: Path) -> None:
        doc = Document(path=tmp_path / "test.pdf")
        doc.mark(ProcessingStatus.FAILED)
        assert doc.has_failed

    def test_add_warning(self, tmp_path: Path) -> None:
        doc = Document(path=tmp_path / "test.pdf")
        doc.add_warning("disk space low")
        assert "disk space low" in doc.warnings

    def test_add_error(self, tmp_path: Path) -> None:
        doc = Document(path=tmp_path / "test.pdf")
        doc.add_error("file corrupt")
        assert "file corrupt" in doc.errors

    def test_id_from_checksum(self, tmp_path: Path) -> None:
        doc = Document(path=tmp_path / "test.pdf", checksum="abc123")
        assert doc.id == "abc123"

    def test_id_fallback(self, tmp_path: Path) -> None:
        doc = Document(path=tmp_path / "test.pdf")
        assert len(doc.id) == 16  # SHA-256 truncated

    def test_properties(self, tmp_path: Path) -> None:
        doc = Document(path=tmp_path / "test.pdf", filename="test.pdf", extension=".pdf", size=1024)
        assert doc.filename == "test.pdf"
        assert doc.extension == ".pdf"
        assert doc.size == 1024


class TestProcessingStatus:
    """Verify the ProcessingStatus enum."""

    def test_all_defined(self) -> None:
        expected = [
            "discovered", "validated", "queued", "running",
            "completed", "failed", "skipped",
        ]
        for e in expected:
            assert ProcessingStatus(e).value == e

    def test_string_representation(self) -> None:
        assert str(ProcessingStatus.COMPLETED) == "completed"
        assert str(ProcessingStatus.FAILED) == "failed"


class TestProcessingResult:
    """Verify the ProcessingResult aggregation."""

    def test_empty_result(self) -> None:
        result = ProcessingResult()
        assert result.discovered == 0
        assert result.processed == 0
        assert result.failed == 0
        assert result.skipped == 0

    def test_with_documents(self, tmp_path: Path) -> None:
        d1 = Document(path=tmp_path / "a.pdf"); d1.mark(ProcessingStatus.COMPLETED)
        d2 = Document(path=tmp_path / "b.pdf"); d2.mark(ProcessingStatus.FAILED)
        d3 = Document(path=tmp_path / "c.pdf"); d3.mark(ProcessingStatus.SKIPPED)
        result = ProcessingResult(documents=[d1, d2, d3])
        assert result.discovered == 3
        assert result.processed == 1
        assert result.failed == 1
        assert result.skipped == 1

    def test_merge(self, tmp_path: Path) -> None:
        r1 = ProcessingResult(documents=[Document(path=tmp_path / "a.pdf")])
        r2 = ProcessingResult(documents=[Document(path=tmp_path / "b.pdf")])
        r1.merge(r2)
        assert r1.discovered == 2


# =========================================================================
# Scanner
# =========================================================================

class TestDocumentScanner:
    """Verify recursive document discovery."""

    def test_scan_finds_files(self, temp_dir: Path) -> None:
        scanner = DocumentScanner(root_path=temp_dir)
        docs = scanner.scan()
        assert len(docs) >= 5

    def test_scan_include_extensions(self, temp_dir: Path) -> None:
        scanner = DocumentScanner(root_path=temp_dir, include_extensions=[".pdf"])
        docs = scanner.scan()
        assert all(d.extension == ".pdf" for d in docs)
        assert len(docs) == 2  # test.pdf + subdir/nested.pdf

    def test_scan_nonexistent_dir(self) -> None:
        scanner = DocumentScanner(root_path=Path("/nonexistent/path"))
        docs = scanner.scan()
        assert docs == []

    def test_scan_exclude_pattern(self, temp_dir: Path) -> None:
        scanner = DocumentScanner(root_path=temp_dir, exclude_patterns=["*.xyz"])
        docs = scanner.scan()
        assert all(d.extension != ".xyz" for d in docs)

    def test_scan_recursive(self, temp_dir: Path) -> None:
        scanner = DocumentScanner(root_path=temp_dir)
        docs = scanner.scan()
        filenames = [d.filename for d in docs]
        assert "nested.pdf" in filenames


# =========================================================================
# Validator
# =========================================================================

class TestDocumentValidator:
    """Verify document validation."""

    def test_valid_document(self, temp_dir: Path) -> None:
        doc = Document(path=temp_dir / "test.pdf", extension=".pdf")
        validator = DocumentValidator(supported_extensions=[".pdf"])
        assert validator.validate(doc)
        assert doc.status == ProcessingStatus.VALIDATED

    def test_file_not_found(self) -> None:
        doc = Document(path=Path("/nonexistent/file.pdf"))
        validator = DocumentValidator()
        assert not validator.validate(doc)
        assert doc.has_failed

    def test_unsupported_extension(self, temp_dir: Path) -> None:
        doc = Document(path=temp_dir / "unsupported.xyz", extension=".xyz")
        validator = DocumentValidator(supported_extensions=[".pdf", ".xlsx"])
        assert not validator.validate(doc)
        assert doc.status == ProcessingStatus.SKIPPED

    def test_empty_file(self, temp_dir: Path, empty_file: Path) -> None:
        doc = Document(path=empty_file, extension=".pdf", size=0)
        validator = DocumentValidator(supported_extensions=[".pdf"])
        assert not validator.validate(doc)
        assert doc.has_failed

    def test_duplicate_checksum(self, temp_dir: Path) -> None:
        doc1 = Document(path=temp_dir / "test.pdf", checksum="same")
        doc2 = Document(path=temp_dir / "test.png", checksum="same")
        validator = DocumentValidator(supported_extensions=[".pdf", ".png"])
        assert validator.validate(doc1)
        assert not validator.validate(doc2)
        assert doc2.status == ProcessingStatus.SKIPPED

    def test_reset(self, temp_dir: Path) -> None:
        doc = Document(path=temp_dir / "test.pdf", checksum="dup")
        validator = DocumentValidator(supported_extensions=[".pdf", ".png"])
        validator.validate(doc)
        validator.reset()
        doc2 = Document(path=temp_dir / "test.png", checksum="dup")
        assert validator.validate(doc2)


# =========================================================================
# Metadata Extractor
# =========================================================================

class TestMetadataExtractor:
    """Verify filesystem metadata extraction."""

    def test_extract_basic(self, temp_dir: Path) -> None:
        doc = Document(path=temp_dir / "test.pdf", extension=".pdf")
        extractor = MetadataExtractor()
        extractor.extract(doc)
        assert doc.size > 0
        assert doc.checksum != ""
        assert doc.metadata["extension"] == ".pdf"
        assert doc.metadata["filename"] == "test.pdf"

    def test_checksum_consistent(self, temp_dir: Path) -> None:
        doc = Document(path=temp_dir / "test.pdf")
        extractor = MetadataExtractor()
        extractor.extract(doc)
        expected = hashlib.sha256(b"dummy pdf content").hexdigest()
        assert doc.checksum == expected

    def test_timestamps(self, temp_dir: Path) -> None:
        doc = Document(path=temp_dir / "test.pdf")
        extractor = MetadataExtractor()
        extractor.extract(doc)
        assert "created" in doc.metadata
        assert "modified" in doc.metadata
        assert "accessed" in doc.metadata

    def test_nonexistent_file(self) -> None:
        doc = Document(path=Path("/nonexistent/file.pdf"))
        extractor = MetadataExtractor()
        extractor.extract(doc)
        assert doc.checksum == ""


# =========================================================================
# Parser Registry
# =========================================================================

class TestParserRegistry:
    """Verify extension-to-parser mapping."""

    def test_register_and_lookup(self) -> None:
        registry = ParserRegistry()
        registry.register(StubPDFParser)
        parser = registry.lookup(".pdf")
        assert parser is not None
        assert isinstance(parser, StubPDFParser)

    def test_lookup_nonexistent(self) -> None:
        registry = ParserRegistry()
        assert registry.lookup(".xyz") is None

    def test_supported_extensions(self) -> None:
        registry = ParserRegistry()
        registry.register(StubPDFParser)
        registry.register(StubExcelParser)
        registry.register(StubImageParser)
        assert ".pdf" in registry.supported_extensions
        assert ".xlsx" in registry.supported_extensions
        assert ".png" in registry.supported_extensions
        assert ".dbc" not in registry.supported_extensions

    def test_parser_names(self) -> None:
        registry = ParserRegistry()
        registry.register(StubPDFParser)
        registry.register(StubExcelParser)
        assert "PDFParser" in registry.parser_names
        assert "ExcelParser" in registry.parser_names

    def test_override_warning(self) -> None:
        registry = ParserRegistry()
        registry.register(StubPDFParser)
        # Registering another parser for .pdf should warn but succeed
        registry.register(StubPDFParser)  # Same parser, fine


# =========================================================================
# Stub Parsers
# =========================================================================

class TestStubParsers:
    """Verify each stub parser registers correctly and returns expected types."""

    def test_pdf_parser(self) -> None:
        parser = StubPDFParser()
        assert parser.parser_name == "PDFParser"
        assert ".pdf" in parser.supported_extensions

    def test_excel_parser(self) -> None:
        parser = StubExcelParser()
        assert parser.parser_name == "ExcelParser"
        assert ".xlsx" in parser.supported_extensions
        assert ".xls" in parser.supported_extensions

    def test_image_parser(self) -> None:
        parser = StubImageParser()
        assert parser.parser_name == "ImageParser"
        assert ".png" in parser.supported_extensions
        assert ".jpg" in parser.supported_extensions

    def test_dbc_parser(self) -> None:
        parser = StubDBCParser()
        assert parser.parser_name == "DBCParser"
        assert ".dbc" in parser.supported_extensions

    def test_parse_returns_result(self, tmp_path: Path) -> None:
        doc = Document(path=tmp_path / "test.pdf", filename="test.pdf")
        parser = StubPDFParser()
        result = parser.parse(doc)
        assert isinstance(result, ProcessingResult)
        assert doc.status == ProcessingStatus.COMPLETED


# =========================================================================
# Base Parser
# =========================================================================

class TestBaseParser:
    """Verify BaseParser enforces the parser contract."""

    def test_cannot_instantiate_base(self) -> None:
        with pytest.raises(TypeError):
            BaseParser()  # type: ignore  # abstract

    def test_concrete_parser_has_required(self) -> None:
        parser = StubPDFParser()
        assert hasattr(parser, "supported_extensions")
        assert hasattr(parser, "parser_name")
        assert hasattr(parser, "validate")
        assert hasattr(parser, "parse")
        assert hasattr(parser, "normalize")
        assert hasattr(parser, "cleanup")

    def test_default_methods(self) -> None:
        parser = StubPDFParser()
        doc = Document(path=Path("test.pdf"))
        assert parser.validate(doc) is True  # default
        # normalize and cleanup should not raise
        parser.normalize(doc)
        parser.cleanup(doc)


# =========================================================================
# Pipeline Integration
# =========================================================================

class TestIngestionPipeline:
    """Verify the end-to-end ingestion pipeline with stub parsers."""

    def _stub_pipeline(self) -> IngestionPipeline:
        """Create a pipeline that uses stub parsers (not real processors)."""
        p = IngestionPipeline()
        p.registry.register(StubPDFParser)
        p.registry.register(StubExcelParser)
        p.registry.register(StubImageParser)
        p.registry.register(StubDBCParser)
        return p

    def test_pipeline_with_temp_files(self, temp_dir: Path) -> None:
        pipeline = self._stub_pipeline()
        result = pipeline.run(temp_dir)
        assert result.discovered >= 5
        assert result.processed >= 4  # .xyz extension won't have a parser
        assert result.failed == 0
        skipped = [d for d in result.documents if d.status == ProcessingStatus.SKIPPED]
        assert all("xyz" in d.filename for d in skipped)

    def test_pipeline_with_empty_dir(self, tmp_path: Path) -> None:
        pipeline = self._stub_pipeline()
        result = pipeline.run(tmp_path)
        assert result.discovered == 0
        assert result.processed == 0

    def test_pipeline_include_only_pdf(self, temp_dir: Path) -> None:
        pipeline = self._stub_pipeline()
        result = pipeline.run(temp_dir, include_extensions=[".pdf"])
        assert result.discovered == 2  # test.pdf + nested.pdf
        assert result.processed == 2

    def test_pipeline_report_format(self, temp_dir: Path) -> None:
        pipeline = self._stub_pipeline()
        result = pipeline.run(temp_dir)
        report = pipeline.report(result)
        assert "Processing Summary" in report
        assert "Discovered:" in report
        assert "Processed:" in report
        assert "Failed:" in report
        assert "Skipped:" in report


# =========================================================================
# File listing test
# =========================================================================

class TestDatasetFiles:
    """Verify the synthetic dataset was placed correctly."""

    def test_raw_directory_has_files(self) -> None:
        raw = Path("data/raw")
        assert raw.exists(), "data/raw/ directory must exist"
        files = list(raw.iterdir())
        assert len(files) > 0, "data/raw/ must contain test files"
        pdfs = [f for f in files if f.suffix == ".pdf"]
        xlsx = [f for f in files if f.suffix == ".xlsx"]
        pngs = [f for f in files if f.suffix == ".png"]
        assert len(pdfs) >= 1, "Missing PDF in data/raw/"
        assert len(xlsx) >= 1, "Missing XLSX in data/raw/"
        assert len(pngs) >= 1, "Missing PNG in data/raw/"
