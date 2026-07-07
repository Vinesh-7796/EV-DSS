"""Processing summary reporter.

Generates a human-readable summary of an ingestion pipeline run,
showing counts of discovered, processed, failed, and skipped documents.
"""

from typing import List

from backend.logger import logger
from ingestion.models import Document, ProcessingResult


class ProcessingReporter:
    """Formats and displays ingestion pipeline results."""

    def report(self, result: ProcessingResult) -> str:
        """Generate a formatted processing summary.

        Args:
            result: The aggregated result from the pipeline.

        Returns:
            A multi-line string with the summary and per-document results.
        """
        lines: List[str] = []
        lines.append("")
        lines.append("Processing Summary")
        lines.append("-" * 40)

        for doc in result.documents:
            status_icon = self._status_icon(doc)
            lines.append(f"  {status_icon} {doc.filename}")
            if doc.errors:
                for err in doc.errors:
                    lines.append(f"         Error: {err}")
            if doc.warnings:
                for warn in doc.warnings:
                    lines.append(f"         Warning: {warn}")

        lines.append("")
        lines.append(f"  Discovered:  {result.discovered}")
        lines.append(f"  Processed:   {result.processed}")
        lines.append(f"  Failed:      {result.failed}")
        lines.append(f"  Skipped:     {result.skipped}")
        lines.append(f"  Duration:    {result.duration_s:.2f}s")
        lines.append("-" * 40)
        lines.append("")

        summary = "\n".join(lines)
        logger.info("Processing summary: {} discovered, {} processed, {} failed, {} skipped",
                     result.discovered, result.processed, result.failed, result.skipped)
        return summary

    def log_report(self, result: ProcessingResult) -> None:
        """Log each document's result at INFO level.

        Args:
            result: The aggregated result from the pipeline.
        """
        for doc in result.documents:
            if doc.status.value == "completed":
                logger.info("  [OK] {}", doc.filename)
            elif doc.status.value == "skipped":
                logger.info("  [/] {} (skipped)", doc.filename)
            elif doc.status.value == "failed":
                logger.error("  [!!] {} (failed: {})", doc.filename, "; ".join(doc.errors))

    @staticmethod
    def _status_icon(doc: Document) -> str:
        from ingestion.models import ProcessingStatus
        mapping = {
            ProcessingStatus.COMPLETED: "[OK]",
            ProcessingStatus.FAILED:    "[!!]",
            ProcessingStatus.SKIPPED:   "[/]",
            ProcessingStatus.DISCOVERED: "[  ]",
            ProcessingStatus.VALIDATED: "[ok]",
            ProcessingStatus.RUNNING:   "[> ]",
        }
        return mapping.get(doc.status, "[??]")
