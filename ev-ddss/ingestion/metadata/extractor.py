"""Metadata extraction from filesystem attributes.

Computes checksum (SHA-256), file size, timestamps, and basic
file properties WITHOUT opening or parsing the document contents.
"""

import hashlib
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from backend.logger import logger
from ingestion.models import Document


class MetadataExtractor:
    """Extracts filesystem-level metadata from documents.

    All extraction happens via os.path / pathlib and hashlib.
    No document content is interpreted or parsed.
    """

    def extract(self, document: Document) -> Document:
        """Populate document metadata from the filesystem.

        Computes checksum, size (if not already set), and timestamps.
        Updates the document in place and returns it.

        Args:
            document: Document whose metadata will be populated.

        Returns:
            The same Document instance with metadata filled in.
        """
        path = document.path

        # Size (if not already set)
        if document.size == 0 and path.exists():
            document.size = path.stat().st_size

        # Checksum (SHA-256, streamed to avoid loading entire file)
        if not document.checksum and path.exists():
            document.checksum = self._compute_sha256(path)

        # Filesystem timestamps
        if path.exists():
            stat = path.stat()
            document.metadata["created"] = _timestamp_to_iso(stat.st_ctime)
            document.metadata["modified"] = _timestamp_to_iso(stat.st_mtime)
            document.metadata["accessed"] = _timestamp_to_iso(stat.st_atime)

        # Basic file information
        document.metadata["extension"] = document.extension
        document.metadata["filename"] = document.filename
        document.metadata["size_bytes"] = document.size
        document.metadata["checksum_sha256"] = document.checksum
        document.metadata["dirname"] = str(path.parent.resolve())

        logger.debug("Extracted metadata for {}", document.filename)
        return document

    @staticmethod
    def _compute_sha256(path: Path) -> str:
        """Compute the SHA-256 hex digest of a file using streaming reads.

        Args:
            path: Path to the file.

        Returns:
            Lowercase hex string of the SHA-256 digest.
        """
        hasher = hashlib.sha256()
        try:
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    hasher.update(chunk)
        except OSError as exc:
            logger.warning("Failed to compute checksum for {}: {}", path.name, exc)
            return ""
        return hasher.hexdigest()


def _timestamp_to_iso(timestamp: float) -> str:
    """Convert a Unix timestamp to ISO 8601 string."""
    try:
        return datetime.fromtimestamp(timestamp).isoformat()
    except (OSError, ValueError):
        return datetime.fromtimestamp(time.time()).isoformat()
