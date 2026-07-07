"""Stub Excel parser for Phase 1 ingestion framework.

Logs parser selection. Full Excel workbook extraction will be implemented
in a future phase.
"""

from typing import List

from backend.logger import logger
from ingestion.base.parser import BaseParser
from ingestion.models import Document, ProcessingResult, ProcessingStatus


class ExcelParser(BaseParser):
    """Stub parser for Microsoft Excel workbooks (.xlsx, .xls)."""

    @property
    def supported_extensions(self) -> List[str]:
        return [".xlsx", ".xls"]

    @property
    def parser_name(self) -> str:
        return "ExcelParser"

    def parse(self, document: Document) -> ProcessingResult:
        logger.info("ExcelParser selected for {}", document.filename)
        document.mark(ProcessingStatus.COMPLETED)
        return ProcessingResult(
            documents=[document],
            parser_name=self.parser_name,
        )
