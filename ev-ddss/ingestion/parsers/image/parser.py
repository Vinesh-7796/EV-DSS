"""Stub image parser for Phase 1 ingestion framework.

Logs parser selection. Full OCR-based text extraction will be implemented
in a future phase.
"""

from typing import List

from backend.logger import logger
from ingestion.base.parser import BaseParser
from ingestion.models import Document, ProcessingResult, ProcessingStatus


class ImageParser(BaseParser):
    """Stub parser for raster image files (.png, .jpg, .jpeg, .tiff)."""

    @property
    def supported_extensions(self) -> List[str]:
        return [".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp"]

    @property
    def parser_name(self) -> str:
        return "ImageParser"

    def parse(self, document: Document) -> ProcessingResult:
        logger.info("ImageParser selected for {}", document.filename)
        document.mark(ProcessingStatus.COMPLETED)
        return ProcessingResult(
            documents=[document],
            parser_name=self.parser_name,
        )
