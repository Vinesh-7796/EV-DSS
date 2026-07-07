"""Stub DBC parser for Phase 1 ingestion framework.

Logs parser selection. Full CAN database (DBC) parsing will be implemented
in a future phase.
"""

from typing import List

from backend.logger import logger
from ingestion.base.parser import BaseParser
from ingestion.models import Document, ProcessingResult, ProcessingStatus


class DBCParser(BaseParser):
    """Stub parser for Vector CAN database files (.dbc)."""

    @property
    def supported_extensions(self) -> List[str]:
        return [".dbc"]

    @property
    def parser_name(self) -> str:
        return "DBCParser"

    def parse(self, document: Document) -> ProcessingResult:
        logger.info("DBCParser selected for {}", document.filename)
        document.mark(ProcessingStatus.COMPLETED)
        return ProcessingResult(
            documents=[document],
            parser_name=self.parser_name,
        )
