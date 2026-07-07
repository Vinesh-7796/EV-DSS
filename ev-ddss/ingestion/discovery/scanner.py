"""Recursive document discovery from the configured raw data directory.

Walks the filesystem tree, collects all files, and produces Document
instances without reading file contents.
"""

from pathlib import Path
from typing import List, Optional

from backend.logger import logger
from ingestion.models import Document, ProcessingStatus


class DocumentScanner:
    """Scans a root directory recursively for documents.

    Supports include and exclude glob patterns for filtering.
    """

    def __init__(
        self,
        root_path: Path,
        include_extensions: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
    ) -> None:
        """Initialize the scanner.

        Args:
            root_path: Root directory to scan recursively.
            include_extensions: If set, only include files with these
                extensions (e.g. ['.pdf', '.xlsx']).
            exclude_patterns: Glob patterns to exclude from scanning.
        """
        self.root_path: Path = Path(root_path).resolve()
        self.include_extensions: Optional[List[str]] = include_extensions
        self.exclude_patterns: List[str] = exclude_patterns or []

        if not self.root_path.exists():
            logger.warning("Scanner root does not exist: {}", self.root_path)

    def scan(self) -> List[Document]:
        """Recursively discover all documents in the root path.

        Returns:
            A list of Document instances in DISCOVERED status.
        """
        documents: List[Document] = []

        if not self.root_path.exists():
            logger.error("Cannot scan: directory not found - {}", self.root_path)
            return documents

        for file_path in self.root_path.rglob("*"):
            if not file_path.is_file():
                continue

            if self._is_excluded(file_path):
                continue

            ext = file_path.suffix.lower()
            if self.include_extensions and ext not in self.include_extensions:
                continue

            doc = Document(
                path=file_path,
                filename=file_path.name,
                extension=ext,
                size=self._safe_size(file_path),
                status=ProcessingStatus.DISCOVERED,
            )
            documents.append(doc)

        logger.info(
            "Scanner found {} document(s) in {}",
            len(documents),
            self.root_path,
        )
        return documents

    def _is_excluded(self, file_path: Path) -> bool:
        """Check if a file matches any exclude pattern."""
        import fnmatch
        for pattern in self.exclude_patterns:
            if fnmatch.fnmatch(str(file_path), pattern):
                return True
        return False

    @staticmethod
    def _safe_size(file_path: Path) -> int:
        """Get file size safely, returning 0 on error."""
        try:
            return file_path.stat().st_size
        except OSError:
            return 0

    def __repr__(self) -> str:
        return f"DocumentScanner({self.root_path})"
