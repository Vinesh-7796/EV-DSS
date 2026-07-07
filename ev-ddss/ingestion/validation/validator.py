"""Document validation layer.

Verifies each document meets baseline requirements before parser selection:
    - File exists on disk
    - File is readable
    - Extension is supported by the registry
    - File is not empty
    - Checksum is not a duplicate of an already-validated document
"""

from pathlib import Path
from typing import Dict, List, Optional, Set

from backend.logger import logger
from ingestion.models import Document, ProcessingStatus


class DocumentValidator:
    """Validates documents before they enter the parsing pipeline.

    Maintains a set of seen checksums to detect duplicates.
    """

    def __init__(self, supported_extensions: Optional[List[str]] = None) -> None:
        """Initialize the validator.

        Args:
            supported_extensions: List of allowed file extensions.
                If None, all extensions pass extension checks.
        """
        self.supported_extensions: Optional[List[str]] = supported_extensions
        self._seen_checksums: Set[str] = set()

    def validate(self, document: Document) -> bool:
        """Run all validation checks against a document.

        Checks are executed in order of cost (fastest first) so that
        cheap failures short-circuit expensive ones.

        Args:
            document: The document to validate. Status and errors are
                updated in-place.

        Returns:
            True if the document passes all checks, False otherwise.
        """
        path = document.path

        # 1. Exists
        if not path.exists():
            document.add_error(f"File not found: {path}")
            document.mark(ProcessingStatus.FAILED)
            return False

        # 2. Readable
        if not os_access_readable(path):
            document.add_error(f"File not readable: {path}")
            document.mark(ProcessingStatus.FAILED)
            return False

        # 3. Extension check
        if self.supported_extensions is not None:
            ext = document.extension
            if ext not in self.supported_extensions:
                document.add_warning(
                    f"Unsupported extension '{ext}'. "
                    f"Supported: {self.supported_extensions}"
                )
                document.mark(ProcessingStatus.SKIPPED)
                return False

        # 4. Not empty (check actual filesystem size as fallback)
        actual_size = document.size
        if actual_size == 0:
            try:
                actual_size = path.stat().st_size
            except OSError:
                pass
        if actual_size == 0:
            document.add_error(f"File is empty: {path}")
            document.mark(ProcessingStatus.FAILED)
            return False

        # 5. Duplicate checksum (requires checksum to already be computed)
        if document.checksum:
            if document.checksum in self._seen_checksums:
                document.add_warning(f"Duplicate document (checksum: {document.checksum[:12]}...)")
                document.mark(ProcessingStatus.SKIPPED)
                return False
            self._seen_checksums.add(document.checksum)

        document.mark(ProcessingStatus.VALIDATED)
        return True

    def reset(self) -> None:
        """Clear the seen-checksum set (e.g. for a new pipeline run)."""
        self._seen_checksums.clear()


def os_access_readable(path: Path) -> bool:
    """Check if a file is readable using os.access."""
    import os
    try:
        return os.access(path, os.R_OK)
    except OSError:
        return False
