#!/usr/bin/env python3
"""EV Diagnostic Decision Support System (EV-DDSS) - Application Entry Point.

Usage:
    python main.py              # Start the server
    python main.py --help       # Show usage information
"""

import sys
from pathlib import Path

# Ensure the project root is on sys.path for consistent imports
_project_root = Path(__file__).resolve().parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import typer
import uvicorn

from backend.logger import setup_logger, logger
from config import get_settings
from database.connection import get_database
from database.qdrant import get_qdrant
from ingestion.pipeline.pipeline import IngestionPipeline
from processing.pipeline_intelligence import DocumentIntelligencePipeline
from processing.report import ProcessingReport

cli = typer.Typer(
    name="ev-ddss",
    help="EV Diagnostic Decision Support System",
    add_completion=False,
)


def print_banner(settings) -> None:
    """Print the application startup banner."""
    import platform

    banner = f"""
{'-'*44}
  EV Diagnostic Decision Support System
  Version {settings.application.version}

  Python      {platform.python_version()}
  Host        {settings.application.host}:{settings.application.port}
  Debug       {settings.application.debug}
{'-'*44}
"""
    print(banner)


def print_status(database_ok: bool, qdrant_ok: bool, config_ok: bool, log_ok: bool) -> None:
    """Print component status summary."""
    def _icon(ok: bool) -> str:
        return "[OK]" if ok else "[!!]"

    print(f"  Configuration  {_icon(config_ok)}  {'Loaded' if config_ok else 'Failed'}")
    print(f"  Logger         {_icon(log_ok)}  {'Initialized' if log_ok else 'Failed'}")
    print(f"  Database       {_icon(database_ok)}  {'Connected' if database_ok else 'Disconnected'}")
    print(f"  Qdrant         {_icon(qdrant_ok)}  {'Connected' if qdrant_ok else 'Disconnected'}")
    print(f"  FastAPI        [OK]  Started")
    print(f"\n  Environment Ready")
    print(f"{'-'*44}\n")


@cli.command()
def start() -> None:
    """Initialize and start the EV-DDSS server."""
    # ── Configuration ──
    try:
        settings = get_settings(reload=True)
        config_ok = True
    except Exception as exc:
        print(f"FATAL: Configuration load failed: {exc}")
        sys.exit(1)

    # ── Logging ──
    try:
        setup_logger()
        log_ok = True
    except Exception as exc:
        print(f"FATAL: Logger initialization failed: {exc}")
        sys.exit(1)

    logger.info("EV-DDSS starting - version {}", settings.application.version)

    # ── Database ──
    database_ok = False
    try:
        db = get_database()
        db.connect()
        database_ok = db.is_connected
        logger.info("Database: connected")
    except Exception as exc:
        logger.warning("Database: connection failed - {}", exc)
        database_ok = False

    # ── Qdrant ──
    qdrant_ok = False
    try:
        qdrant = get_qdrant()
        qdrant.connect()
        qdrant_ok = qdrant.is_connected
        logger.info("Qdrant: connected")
    except Exception as exc:
        logger.warning("Qdrant: connection failed - {}", exc)
        qdrant_ok = False

    # ── Banner ──
    print_banner(settings)
    print_status(database_ok, qdrant_ok, config_ok, log_ok)

    # ── Start FastAPI ──
    logger.info(
        "Starting FastAPI on {}:{}",
        settings.application.host,
        settings.application.port,
    )
    uvicorn.run(
        "backend.api.server:create_app",
        host=settings.application.host,
        port=settings.application.port,
        reload=settings.application.debug,
        log_level=settings.application.log_level.lower(),
        factory=True,
    )


@cli.command()
def ingest(
    path: str = typer.Option(
        "data/raw",
        "--path",
        "-p",
        help="Root directory to scan for documents",
    ),
    setup_logging: bool = typer.Option(
        True,
        "--log/--no-log",
        help="Enable logging output",
    ),
) -> None:
    """Run the document ingestion pipeline.

    Discovers documents in PATH, validates them, extracts metadata,
    selects the appropriate parser, and produces a processing summary.
    """
    if setup_logging:
        setup_logger()

    logger.info("Ingestion command invoked: path={}", path)

    pipeline = IngestionPipeline()
    pipeline.register_default_parsers()

    root = _project_root / path
    result = pipeline.run(root)

    summary = pipeline.report(result)
    print(summary)


@cli.command()
def process(
    path: str = typer.Option(
        "data/raw",
        "--path",
        "-p",
        help="Directory containing documents to process",
    ),
    setup_logging: bool = typer.Option(
        True,
        "--log/--no-log",
        help="Enable logging output",
    ),
) -> None:
    """Process engineering documents into standardised JSON output.

    Scans PATH for supported documents (PDF, XLSX, DBC, PNG/JPG),
    runs the appropriate processor, and writes results to data/processed/.
    """
    if setup_logging:
        setup_logger()

    logger.info("Process command invoked: path={}", path)
    pipeline = IngestionPipeline()
    pipeline.register_default_parsers()
    root = _project_root / path
    result = pipeline.run(root)
    summary = pipeline.report(result)
    print(summary)


@cli.command()
def pipeline(
    path: str = typer.Option(
        "data/raw",
        "--path",
        "-p",
        help="Directory containing documents to process",
    ),
    setup_logging: bool = typer.Option(
        True,
        "--log/--no-log",
        help="Enable logging output",
    ),
) -> None:
    """Run the Document Intelligence Pipeline.

    Scans PATH for supported documents, processes each through the
    full intelligence pipeline (parsing → validation → reference gen
    → relationship graph → serialization → knowledge store), and
    prints a detailed summary.
    """
    if setup_logging:
        setup_logger()

    logger.info("Pipeline command invoked: path={}", path)
    root = _project_root / path

    # Scan for documents
    from ingestion.discovery.scanner import DocumentScanner
    from ingestion.validation.validator import DocumentValidator
    from ingestion.metadata.extractor import MetadataExtractor

    scanner = DocumentScanner(root_path=root)
    docs = scanner.scan()
    logger.info("Pipeline: discovered {} documents", len(docs))

    # Validate and extract metadata
    validator = DocumentValidator()
    extractor = MetadataExtractor()
    valid_docs = []
    for doc in docs:
        if validator.validate(doc):
            extractor.extract(doc)
            valid_docs.append(doc)

    logger.info("Pipeline: {} valid documents to process", len(valid_docs))

    if not valid_docs:
        print("No valid documents found to process.")
        return

    # Run the intelligence pipeline
    pipe = DocumentIntelligencePipeline()
    reports = pipe.process_many(valid_docs)

    # Print summary
    successes = [r for r in reports if r.validation_passed]
    failures = [r for r in reports if not r.validation_passed]

    print()
    print("=" * 60)
    print("  Document Intelligence Pipeline - Results")
    print("=" * 60)
    print(f"  Total:      {len(reports)}")
    print(f"  Successful: {len(successes)}")
    print(f"  Failed:     {len(failures)}")
    print()

    for report in reports:
        status = "[PASS]" if report.validation_passed else "[FAIL]"
        stores = ", ".join(report.stored_in) if report.stored_in else "none"
        print(f"  {status} {report.source}")
        print(f"         type={report.doc_type}, nodes={report.node_count}, "
              f"edges={report.edge_count}, time={report.processing_time_s:.2f}s")
        print(f"         stores: {stores}")
        if report.validation_issues:
            for issue in report.validation_issues[:3]:
                print(f"           - {issue}")
            if len(report.validation_issues) > 3:
                print(f"           ... and {len(report.validation_issues) - 3} more")
        print()

    print("=" * 60)
    print(pipe.summary())

    if failures:
        print("\nWARNING: Some documents failed validation. Check logs for details.")
        print("=" * 60)


@cli.command()
def retrieval_build(
    path: str = typer.Option(
        "data/processed",
        "--path",
        "-p",
        help="Directory containing enriched JSON documents",
    ),
    setup_logging: bool = typer.Option(
        True,
        "--log/--no-log",
        help="Enable logging output",
    ),
) -> None:
    """Build all retrieval indexes from enriched CDS documents.

    Scans PATH for enriched JSON documents, runs content selection,
    chunk optimization, embedding generation, and indexes into
    Qdrant, graph, and image stores.
    """
    if setup_logging:
        setup_logger()

    logger.info("Retrieval build command invoked: path={}", path)
    root = _project_root / path

    # Load enriched documents
    from processing.models.models import Document
    from processing.store.json_store import JSONKnowledgeStore

    json_store = JSONKnowledgeStore(root)
    doc_list = json_store.list_documents()

    if not doc_list:
        print("No enriched documents found to index.")
        return

    docs = []
    for entry in doc_list:
        store_id = entry.get("store_id", "")
        if store_id:
            doc = json_store.retrieve(store_id)
            if doc:
                docs.append(doc)

    logger.info("Retrieval build: loaded {} enriched documents", len(docs))

    # Run the retrieval pipeline
    from retrieval.pipeline import RetrievalPipeline

    pipeline = RetrievalPipeline()
    report = pipeline.build(documents=docs)

    print()
    print("=" * 55)
    print("  Retrieval Index Build - Results")
    print("=" * 55)
    print(f"  Documents processed:    {report.documents_processed}")
    print(f"  Total chunks:           {report.total_chunks}")
    print(f"  Vectors indexed:        {report.vectors_indexed}")
    print(f"  Graph entities:         {report.graph_entities}")
    print(f"  Graph edges:            {report.graph_edges}")
    print(f"  Images indexed:         {report.images_indexed}")
    print(f"  SQL records available:  {report.sql_records_available}")
    print(f"  Processing time:        {report.processing_time_s:.2f}s")
    if report.errors:
        print(f"  Errors ({len(report.errors)}):")
        for err in report.errors[:5]:
            print(f"    - {err}")
    print("=" * 55)


@cli.command()
def retrieval_query(
    query: str = typer.Argument(
        ...,
        help="Technician query text",
    ),
    top_k: int = typer.Option(
        10,
        "--top-k",
        "-k",
        help="Top-k results per method",
    ),
    setup_logging: bool = typer.Option(
        True,
        "--log/--no-log",
        help="Enable logging output",
    ),
) -> None:
    """Run a query through the hybrid retrieval engine.

    Returns a structured context package with semantic context, exact
    matches, graph context, image references, and citations.
    """
    if setup_logging:
        setup_logger()

    logger.info("Retrieval query: '{}'", query[:120])

    from retrieval.engine import HybridRetrievalEngine

    engine = HybridRetrievalEngine()
    engine.initialize()
    package = engine.retrieve(query, top_k_vector=top_k, top_k_graph=top_k)

    print()
    print("=" * 55)
    print("  Hybrid Retrieval - Results")
    print("=" * 55)
    print(f"  Query:      {package.query}")
    print(f"  Methods:    {', '.join(package.methods_used)}")
    print(f"  Results:    {package.total_results} ({package.deduplicated_count} deduplicated)")
    print(f"  Confidence: {package.confidence:.4f}")
    print(f"  Latency:    {package.processing_time_ms:.1f}ms")
    print()

    if package.semantic_context:
        print("  ── Semantic Context (vector) ──")
        for r in package.semantic_context[:5]:
            print(f"    [{r.score:.3f}] {r.content[:150]}...")
            print(f"           {r.to_citation()}")
        print()

    if package.exact_matches:
        print("  ── Exact Matches (SQL) ──")
        for r in package.exact_matches[:5]:
            print(f"    [{r.score:.3f}] {r.content[:150]}...")
            print(f"           {r.to_citation()}")
        print()

    if package.graph_context:
        print("  ── Graph Context ──")
        for r in package.graph_context[:5]:
            print(f"    [{r.score:.3f}] {r.content[:150]}...")
            print(f"           {r.to_citation()}")
        print()

    if package.image_references:
        print("  ── Image References ──")
        for r in package.image_references[:3]:
            print(f"    [{r.score:.3f}] {r.content[:150]}...")
            print(f"           {r.to_citation()}")
        print()

    print("  ── Citations ──")
    for c in package.citations[:10]:
        print(f"    - {c}")
    print()
    print("=" * 55)


@cli.command()
def reason(
    query: str = typer.Argument(
        ...,
        help="Technician query text",
    ),
    runtime: str = typer.Option(
        "mock",
        "--runtime",
        "-r",
        help="LLM runtime (ollama, mock)",
    ),
    setup_logging: bool = typer.Option(
        True,
        "--log/--no-log",
        help="Enable logging output",
    ),
) -> None:
    """Run the LLM orchestration engine on a query with mock context.

    For development: generates a minimal StructuredContextPackage and
    runs the full reasoning pipeline.  Use ``--runtime mock`` to test
    without a running model.
    """
    if setup_logging:
        setup_logger()

    logger.info("Reason command: query='{}', runtime={}", query[:120], runtime)

    from reasoning.engine import ReasoningEngine
    from reasoning.config import ReasoningConfig
    from retrieval.models import StructuredContextPackage, RetrievalResult, RetrievalMethod

    # Build a minimal context package for testing
    ctx = StructuredContextPackage(
        query=query,
        semantic_context=[
            RetrievalResult(
                content="The HV battery pack consists of 96 series-connected "
                        "cells with a nominal voltage of 355V.",
                node_id="doc1.n1", node_type="paragraph",
                source="BMS_Manual.pdf", score=0.92,
                method=RetrievalMethod.VECTOR,
                reference={"type": "pdf", "location": {"page": 12}},
            ),
            RetrievalResult(
                content="Error code P0AA6: Hybrid Battery Voltage System "
                        "Isolation Fault. Check isolation resistance.",
                node_id="doc1.n2", node_type="paragraph",
                source="DTC_Reference.pdf", score=0.88,
                method=RetrievalMethod.VECTOR,
            ),
        ],
        citations=[
            "BMS_Manual.pdf p.12  (vector, score=0.92)",
            "DTC_Reference.pdf  (vector, score=0.88)",
        ],
        confidence=0.85,
        methods_used=["vector"],
    )

    engine = ReasoningEngine()
    engine.initialize()
    response = engine.reason(query, ctx)

    print()
    print("=" * 55)
    print("  LLM Orchestration - Diagnostic Response")
    print("=" * 55)
    print(f"  Problem:    {response.problem_summary}")
    print()
    print("  Possible Causes:")
    for i, cause in enumerate(response.possible_causes, 1):
        print(f"    {i}. {cause}")
    print()
    print("  Inspection Steps:")
    for i, step in enumerate(response.inspection_steps, 1):
        print(f"    {i}. {step}")
    print()
    print("  Recommended Actions:")
    for i, action in enumerate(response.recommended_actions, 1):
        print(f"    {i}. {action}")
    print()
    if response.referenced_entities:
        print(f"  Entities: {', '.join(response.referenced_entities)}")
    if response.reasoning_summary:
        print(f"  Reasoning: {response.reasoning_summary}")
    if response.citations:
        print("  Citations:")
        for c in response.citations[:5]:
            print(f"    - {c}")
    print()
    meta = response.metadata or {}
    print(f"  [model={meta.get('model','?')}, intent={meta.get('intent','?')}, "
          f"tokens={meta.get('total_tokens','?')}, "
          f"time={meta.get('total_time_ms','?')}ms]")
    print("=" * 55)


@cli.command()
def test() -> None:
    """Run the test suite using pytest."""
    import subprocess
    result = subprocess.run([sys.executable, "-m", "pytest", "tests/", "-v"], cwd=str(_project_root))
    sys.exit(result.returncode)


if __name__ == "__main__":
    cli()
