"""Citation validation — validates citations against retrieved context metadata.

Profiling instrumentation added.
"""

import time
from typing import Any, List, Dict
from dataclasses import dataclass, field
from pathlib import Path

from backend.logger import logger


@dataclass
class CitationValidationResults:
    """Results of citation validation."""

    valid_citations: List[Any] = field(default_factory=list)
    invalid_citations: List[Any] = field(default_factory=list)

    @property
    def all_citations(self) -> List[Any]:
        return self.valid_citations + self.invalid_citations


@dataclass
class CitationValidationResult:
    citation: str = ""
    is_valid: bool = False
    validator: str = "CitationValidator"
    validation_status: str = "FAIL"
    reason: str = ""
    errors: List[str] = field(default_factory=list)


class CitationValidator:
    """Validates that citations in the diagnostic response match retrieved context metadata."""

    def __init__(self, config: Any = None) -> None:
        self.config = config or {}

    def validate(self, diagnostic_response: Any, context_package: Any) -> Any:
        """Validate citations against retrieved context metadata.

        Parameters
        ----------
        diagnostic_response : Any
            The LLM-generated diagnostic response containing citations.
        context_package : Any
            The Structured Context Package containing retrieved context.

        Returns
        -------
        CitationValidationResults
            Validation results containing valid and invalid citations.
        """
        start = time.time()
        logger.info("CitationValidator: starting validation")

        # Simulate citation validation with profiling
        validation_results = self._validate_citations(diagnostic_response, context_package)
        elapsed_ms = (time.time() - start) * 1000
        logger.info("CitationValidator: completed in %.3f ms, %d total citations",
                     elapsed_ms, len(validation_results.all_citations))

        return validation_results

    def _validate_citations(self, diagnostic_response: Any, context_package: Any) -> Any:
        """Internal citation validation logic."""

        # Get citations from diagnostic response
        citations = self._extract_citations(diagnostic_response)

        # Get context metadata for comparison
        context_metadata = self._extract_context_metadata(context_package)

        # Validate each citation against context metadata
        valid_citations = []
        invalid_citations = []

        for citation in citations:
            # Parse citation text to extract potential metadata
            citation_parts = self._parse_citation_text(citation)

            # Check if citation matches any context metadata
            is_valid = self._is_citation_valid(citation_parts, context_metadata)

            if is_valid:
                valid_citations.append(CitationValidationResult(
                    citation=citation,
                    is_valid=True,
                    validator="CitationValidator",
                    validation_status="PASS",
                    reason="Citation matches retrieved context metadata",
                    errors=[],
                ))
            else:
                invalid_citations.append(CitationValidationResult(
                    citation=citation,
                    is_valid=False,
                    validator="CitationValidator",
                    validation_status="FAIL",
                    reason="Citation does not match any retrieved metadata",
                    errors=["Citation does not match any retrieved metadata"],
                ))

        return CitationValidationResults(
            valid_citations=valid_citations,
            invalid_citations=invalid_citations
        )

    def _extract_citations(self, diagnostic_response: Any) -> List[str]:
        """Extract citations from diagnostic response."""
        if hasattr(diagnostic_response, 'citations'):
            return diagnostic_response.citations
        elif isinstance(diagnostic_response, dict):
            return diagnostic_response.get('citations', [])
        else:
            return []

    def _extract_context_metadata(self, context_package: Any) -> List[Dict[str, Any]]:
        """Extract metadata from context package for comparison."""
        metadata = []

        for attr in ("semantic_context", "exact_matches", "graph_context", "image_references"):
            for result in getattr(context_package, attr, []) or []:
                result_metadata = getattr(result, "metadata", {}) or {}
                reference = getattr(result, "reference", {}) or {}
                if not isinstance(result_metadata, dict):
                    result_metadata = {}
                if not isinstance(reference, dict):
                    reference = {}
                location = reference.get("location", {}) if isinstance(reference, dict) else {}
                metadata.append({
                    "file": result_metadata.get("source") or getattr(result, "source", ""),
                    "page": result_metadata.get("page") or location.get("page", "") or reference.get("page", ""),
                    "section": result_metadata.get("section") or location.get("section", "") or reference.get("section", ""),
                    "table": result_metadata.get("table") or location.get("table", "") or reference.get("table", ""),
                    "row": result_metadata.get("row") or location.get("row", "") or reference.get("row", ""),
                    "node_id": getattr(result, "node_id", ""),
                    "content": getattr(result, "content", ""),
                })

        return metadata

    def _parse_citation_text(self, citation: str) -> Dict[str, Any]:
        """Parse citation text to extract potential metadata."""
        if "|" in citation:
            parts = [part.strip() for part in citation.split("|")]
            file_part = parts[0]
            page = ""
            section = ""
            for part in parts[1:]:
                cleaned = part.split("(", 1)[0].strip()
                marker = cleaned.encode("latin1", errors="ignore").decode("utf-8", errors="ignore")
                if cleaned.lower().startswith("p."):
                    page = cleaned[2:].strip()
                elif cleaned.lower().startswith("section "):
                    section = cleaned[8:].strip()
                elif cleaned.startswith("§") or marker.startswith("§"):
                    section = (marker or cleaned).lstrip("§").strip()
            return {
                "file": file_part,
                "page": page,
                "section": section,
                "error_codes": [],
                "raw": citation,
            }

        # Parse common citation formats
        # ServiceManual.pdf:10.2 P1C21 pattern
        if ":" in citation and "." in citation.split(":")[0]:
            parts = citation.split(":")
            file_part = parts[0]
            rest = parts[1] if len(parts) > 1 else ""

            # Extract page/section from rest
            page = ""
            section = ""
            if "." in rest:
                doc_part, page_part = rest.split(".", 1)
                if " " in page_part:
                    page, section = page_part.split(" ", 1)
                else:
                    page = page_part

            # Extract error codes
            error_codes = [w for w in citation.split() if w.isalnum() and len(w) <= 5 and w[0].isalpha()]

            return {
                "file": file_part.strip(),
                "page": page,
                "section": section,
                "error_codes": error_codes,
                "raw": citation,
            }

        # Alternative format: File.pdf Page.Section ErrorCode
        elif len(citation.split()) >= 3:
            parts = citation.split()
            file_part = parts[0]
            page_part = parts[1] if len(parts) > 1 else ""
            section_part = parts[2] if len(parts) > 2 else ""

            # Determine if it's a page and section
            page = ""
            section = ""
            if "." in page_part:
                page, section = page_part.split(".", 1)
            else:
                page = page_part
                section = section_part if "P" in section_part else ""

            return {
                "file": file_part,
                "page": page,
                "section": section,
                "error_codes": [p for p in parts if len(p) <= 5 and (p.isalpha() or (p[0].isalpha() and p[1:].isdigit()))],
                "raw": citation,
            }

        return {
            "file": citation,
            "page": "",
            "section": "",
            "error_codes": [],
            "raw": citation,
        }

    def _is_citation_valid(self, citation_parts: Dict[str, Any], context_metadata: List[Dict[str, Any]]) -> bool:
        """Check if citation matches any context metadata."""
        if not citation_parts or not context_metadata:
            return False

        raw = str(citation_parts.get("raw") or citation_parts.get("file") or "").lower()
        citation_file = self._normalize_source(citation_parts.get("file", ""))
        file_match = False
        matching_metadata = []
        for meta in context_metadata:
            meta_source = self._normalize_source(meta.get("file", ""))
            meta_blob = " ".join(str(meta.get(k, "")) for k in ("file", "section", "table", "node_id", "content")).lower()
            if (
                citation_file and meta_source and citation_file == meta_source
                or citation_file and citation_file in meta_blob
                or raw and any(part and part in meta_blob for part in raw.replace("|", " ").split())
            ):
                file_match = True
                matching_metadata.append(meta)

        if not file_match:
            return False

        # If file matches, check page and section if provided
        page_match = True
        if citation_parts.get('page'):
            page_match = any(
                citation_parts['page'] == str(meta.get('page'))
                for meta in matching_metadata
            )

        section_match = True
        if citation_parts.get('section'):
            section_match = any(
                citation_parts['section'].lower() in str(meta.get('section') or meta.get("table") or "").lower()
                for meta in matching_metadata
            )

        return page_match and section_match

    @staticmethod
    def _normalize_source(source: str) -> str:
        source = str(source or "").strip().lower()
        if not source:
            return ""
        path = Path(source)
        return path.stem.lower() if path.suffix else source.replace(".pdf", "").replace(".xlsx", "").replace(".dbc", "")
