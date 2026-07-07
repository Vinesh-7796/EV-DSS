"""Ingestion framework for EV-DDSS.

Provides document discovery, validation, parser selection,
orchestration, and reporting. Designed as a pluggable framework
that future parser implementations can extend without modifying
the core ingestion engine.
"""

from ingestion.models import Document, ProcessingStatus, ProcessingResult
from ingestion.pipeline.pipeline import IngestionPipeline

__all__ = [
    "Document",
    "ProcessingStatus",
    "ProcessingResult",
    "IngestionPipeline",
]
