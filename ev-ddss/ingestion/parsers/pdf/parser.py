"""Stub PDF parser for Phase 1 ingestion framework.

Logs parser selection. Full PDF text extraction will be implemented
in a future phase.
"""

from typing import List

from backend.logger import logger
from ingestion.base.parser import BaseParser
from ingestion.models import Document, ProcessingResult, ProcessingStatus


class PDFParser(BaseParser):
    """Stub parser for Adobe PDF documents (.pdf)."""

    @property
    def supported_extensions(self) -> List[str]:
        return [".pdf"]

    @property
    def parser_name(self) -> str:
        return "PDFParser"

    def parse(self, document: Document) -> ProcessingResult:
        logger.info("PDFParser selected for {}", document.filename)
        document.mark(ProcessingStatus.COMPLETED)
        return ProcessingResult(
            documents=[document],
            parser_name=self.parser_name,
        )
