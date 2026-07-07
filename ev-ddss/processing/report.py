"""Processing report for the Document Intelligence Pipeline.

Captures the outcome of a single pipeline run including validation
status, store identifiers, timing, and content statistics.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from processing.models.models import Statistics


@dataclass
class ProcessingReport:
    """Immutable record of a single pipeline execution.

    Attributes
    ----------
    source : str
        Original filename or path of the processed document.
    doc_type : str
        Document type (pdf, excel, dbc, image).
    validation_passed : bool
        Whether the CDS Document passed all validation checks.
    validation_issues : list of str
        Human-readable descriptions of any validation failures.
    store_results : dict
        Mapping of store names to store-specific identifiers.
    processing_time_s : float
        Wall-clock time for the full pipeline run.
    statistics : Statistics | None
        Aggregated CDS statistics from the processed document.
    timestamp : str
        ISO-formatted timestamp of when processing completed.
    """

    source: str = ""
    doc_type: str = ""
    validation_passed: bool = False
    validation_issues: List[str] = field(default_factory=list)
    store_results: Dict[str, str] = field(default_factory=dict)
    processing_time_s: float = 0.0
    statistics: Optional[Statistics] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    # ── Computed properties ─────────────────────

    @property
    def is_healthy(self) -> bool:
        """Whether the document was both valid and stored successfully."""
        return self.validation_passed and len(self.store_results) > 0

    @property
    def stored_in(self) -> List[str]:
        """Names of stores where the document was persisted."""
        return [k for k, v in self.store_results.items() if v]

    @property
    def node_count(self) -> int:
        if self.statistics:
            return self.statistics.total_content_nodes
        return 0

    @property
    def edge_count(self) -> int:
        if self.statistics:
            return self.statistics.total_relationships
        return 0

    # ── Formatting ──────────────────────────────

    def summary(self) -> str:
        """Return a concise one-line summary."""
        status = "PASS" if self.validation_passed else "FAIL"
        stores = ", ".join(self.stored_in) if self.stored_in else "none"
        return (
            f"[{status}] {self.source} ({self.doc_type}) "
            f"| {self.node_count} nodes, {self.edge_count} edges "
            f"| {self.processing_time_s:.2f}s "
            f"| stored in: {stores}"
        )

    def detailed(self) -> str:
        """Return a multi-line detailed report."""
        lines = [
            f"Document:      {self.source}",
            f"Type:          {self.doc_type}",
            f"Status:        {'PASSED' if self.validation_passed else 'FAILED'}",
            f"Time:          {self.processing_time_s:.2f}s",
            f"Timestamp:     {self.timestamp}",
        ]
        if self.statistics:
            s = self.statistics
            lines.append(f"Nodes:         {s.total_content_nodes}")
            lines.append(f"Edges:         {s.total_relationships}")
            lines.append(f"Max depth:     {s.max_depth}")
            if s.node_type_counts:
                lines.append("Node types:")
                for ntype, count in sorted(s.node_type_counts.items()):
                    lines.append(f"  {ntype}: {count}")
        if self.validation_issues:
            lines.append(f"Issues ({len(self.validation_issues)}):")
            for issue in self.validation_issues[:10]:
                lines.append(f"  - {issue}")
            if len(self.validation_issues) > 10:
                lines.append(f"  ... and {len(self.validation_issues) - 10} more")
        if self.store_results:
            lines.append("Stores:")
            for name, sid in self.store_results.items():
                lines.append(f"  {name}: {sid or '(skipped)'}")
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.summary()
