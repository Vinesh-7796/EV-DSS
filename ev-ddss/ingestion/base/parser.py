"""Abstract base class for all document parsers in the ingestion framework.

All concrete parsers (PDF, Excel, Image, DBC, etc.) must inherit from
BaseParser and implement the required abstract methods. The framework
orchestrates calls to validate, parse, normalize, and cleanup.
"""

from abc import ABC, abstractmethod
from typing import List

from ingestion.models import Document, ProcessingResult


class BaseParser(ABC):
    """Abstract parser that defines the contract for all document parsers.

    Subclasses must implement:
        - validate()   : Verify the document can be parsed
        - parse()      : Extract structured content from the document
        - normalize()  : Standardize the extracted content
        - cleanup()    : Release any resources held during parsing
    """

    @property
    @abstractmethod
    def supported_extensions(self) -> List[str]:
        """File extensions this parser can handle (e.g. ['.pdf', '.PDF'])."""
        ...

    @property
    @abstractmethod
    def parser_name(self) -> str:
        """Human-readable name for this parser (e.g. 'PDFParser')."""
        ...

    def validate(self, document: Document) -> bool:
        """Verify the document is suitable for parsing by this parser.

        Override to add document-specific validation beyond what the
        generic validation step provides (e.g. magic bytes, header check).

        Args:
            document: The document to validate.

        Returns:
            True if the document can be parsed, False otherwise.
        """
        _ = document
        return True

    @abstractmethod
    def parse(self, document: Document) -> ProcessingResult:
        """Extract structured content from the document.

        Args:
            document: The document to parse.

        Returns:
            A ProcessingResult with the outcome of parsing.
        """
        ...

    def normalize(self, document: Document) -> None:
        """Standardize and clean up extracted content.

        Override to apply transformations such as whitespace normalization,
        encoding correction, or field mapping.
        """
        pass

    def cleanup(self, document: Document) -> None:
        """Release any resources acquired during parsing.

        Called after parse() completes (or fails) to ensure file handles,
        temporary files, or memory buffers are released.
        """
        pass

    def __repr__(self) -> str:
        return f"{self.parser_name}(extensions={self.supported_extensions})"
