"""Knowledge Base Watcher — monitors the raw documents folder and triggers
selective re-ingestion when files are added, modified or deleted.

Architecture
────────────
    watchdog.Observer (background thread)
        └─ KBEventHandler (FileSystemEventHandler)
               ↓ on change
            IngestionQueue (thread-safe queue)
               ↓ worker thread drains queue
            _ingest_document(path) / _remove_document(path)
               → DocumentIntelligencePipeline (existing AI Core)
               → RetrievalPipeline (existing AI Core)

Changing the LLM model NEVER triggers this service.
Only physical file changes in data/raw/ do.
"""

import hashlib
import json
import queue
import sys
import threading
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# --- logging -----------------------------------------------------------------
try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent / "ev-ddss"
_RAW_DIR = _PROJECT_ROOT / "data" / "raw"
_STORE_DIR = _PROJECT_ROOT / "data" / "store" / "json"
SUPPORTED_EXTENSIONS = {".pdf", ".xlsx", ".dbc", ".png", ".jpg", ".jpeg"}

# Max ingestion log entries kept in memory
_MAX_LOG_ENTRIES = 200


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class IngestionLogEntry:
    """A single entry in the ingestion activity log."""
    timestamp: str
    event: str          # "added" | "modified" | "deleted" | "reindex" | "error"
    filename: str
    status: str         # "queued" | "processing" | "done" | "failed" | "removed"
    detail: str = ""
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class KBStatus:
    """Current state of the knowledge base watcher."""
    watcher_running: bool = False
    monitored_path: str = ""
    queue_depth: int = 0
    total_processed: int = 0
    total_errors: int = 0
    last_event_at: Optional[str] = None
    last_error: Optional[str] = None
    indexed_files: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Internal ingestion helpers
# ---------------------------------------------------------------------------

def _file_hash(path: Path) -> str:
    """Return SHA-256 hex digest of a file (used for change detection)."""
    sha = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha.update(chunk)
    except OSError:
        pass
    return sha.hexdigest()


def _ingest_single(path: Path, log_cb) -> bool:
    """Run the full ingestion → intelligence → retrieval pipeline for one file.

    Returns True on success, False on error.
    Avoids re-importing heavyweight modules on every call by using lazy imports.
    """
    # Ensure ev-ddss is importable
    _ev_root = str(_PROJECT_ROOT)
    if _ev_root not in sys.path:
        sys.path.insert(0, _ev_root)

    try:
        from ingestion.discovery.scanner import DocumentScanner
        from ingestion.validation.validator import DocumentValidator
        from ingestion.metadata.extractor import MetadataExtractor
        from processing.pipeline_intelligence import DocumentIntelligencePipeline
        from retrieval.pipeline import RetrievalPipeline
        from processing.models.models import Document
        from processing.store.json_store import JSONKnowledgeStore
        import time as _time

        t0 = _time.time()
        log_cb(f"Parsing {path.name}")

        # 1. Scan/validate/extract metadata for this single file
        scanner = DocumentScanner(root_path=path.parent)
        docs = [d for d in scanner.scan() if Path(d.path).resolve() == path.resolve()]
        if not docs:
            log_cb(f"Scanner could not find {path.name}")
            return False

        validator = DocumentValidator()
        extractor = MetadataExtractor()
        valid_docs = []
        for d in docs:
            if validator.validate(d):
                extractor.extract(d)
                valid_docs.append(d)

        if not valid_docs:
            log_cb(f"Document failed validation: {path.name}")
            return False

        # 2. Intelligence pipeline (parsing → CDS → store)
        log_cb(f"Embedding {path.name}")
        pipe = DocumentIntelligencePipeline()
        reports = pipe.process_many(valid_docs)

        if not any(r.validation_passed for r in reports):
            log_cb(f"Intelligence pipeline failed for {path.name}")
            return False

        # 3. Retrieval pipeline (vector + graph indexes)
        log_cb(f"Graph Updated — {path.name}")
        json_store = JSONKnowledgeStore(_STORE_DIR)
        doc_list = json_store.list_documents()
        enriched_docs = []
        stem = path.stem
        for entry in doc_list:
            store_id = entry.get("store_id", "")
            if stem in store_id:
                doc = json_store.retrieve(store_id)
                if doc:
                    enriched_docs.append(doc)

        if enriched_docs:
            ret_pipe = RetrievalPipeline()
            ret_pipe.build(documents=enriched_docs)

        elapsed = (_time.time() - t0) * 1000
        log_cb(f"Retrieval Ready — {path.name} ({elapsed:.0f}ms)")
        return True

    except Exception as exc:
        log_cb(f"ERROR: {exc}")
        return False


def _remove_single(path: Path, log_cb) -> bool:
    """Remove a document from the JSON store and manifest."""
    _ev_root = str(_PROJECT_ROOT)
    if _ev_root not in sys.path:
        sys.path.insert(0, _ev_root)

    try:
        from processing.store.json_store import JSONKnowledgeStore

        json_store = JSONKnowledgeStore(_STORE_DIR)
        stem = path.stem
        removed = False
        for entry in list(json_store.list_documents()):
            store_id = entry.get("store_id", "")
            doc_stem = store_id.split("/", 1)[1] if "/" in store_id else store_id
            if doc_stem == stem:
                json_store.delete(store_id)
                removed = True
                log_cb(f"Removed {path.name} from knowledge base")
        if not removed:
            log_cb(f"{path.name} was not in knowledge base (no-op)")
        return True
    except Exception as exc:
        log_cb(f"ERROR removing {path.name}: {exc}")
        return False


# ---------------------------------------------------------------------------
# Watchdog Event Handler
# ---------------------------------------------------------------------------

class _KBEventHandler:
    """Minimal file-system event handler (watchdog-compatible interface)."""

    def __init__(self, event_q: queue.Queue, log_cb) -> None:
        self._q = event_q
        self._log = log_cb
        self._debounce: Dict[str, float] = {}
        self._debounce_s = 2.0  # seconds to wait before queuing duplicate events

    def _eligible(self, path: str) -> bool:
        return Path(path).suffix.lower() in SUPPORTED_EXTENSIONS

    def _debounced(self, path: str) -> bool:
        now = time.monotonic()
        last = self._debounce.get(path, 0.0)
        if now - last < self._debounce_s:
            return True
        self._debounce[path] = now
        return False

    def on_created(self, event) -> None:
        if event.is_directory:
            return
        path = event.src_path
        if self._eligible(path) and not self._debounced(path):
            self._q.put(("add", Path(path)))

    def on_modified(self, event) -> None:
        if event.is_directory:
            return
        path = event.src_path
        if self._eligible(path) and not self._debounced(path):
            self._q.put(("modify", Path(path)))

    def on_deleted(self, event) -> None:
        if event.is_directory:
            return
        path = event.src_path
        if self._eligible(path):
            self._q.put(("delete", Path(path)))

    def on_moved(self, event) -> None:
        if event.is_directory:
            return
        if self._eligible(event.dest_path):
            self._q.put(("add", Path(event.dest_path)))
        if self._eligible(event.src_path):
            self._q.put(("delete", Path(event.src_path)))


# ---------------------------------------------------------------------------
# KB Watcher
# ---------------------------------------------------------------------------

class KBWatcher:
    """Monitors data/raw/ and automatically runs selective re-ingestion.

    Usage::

        watcher = KBWatcher()
        watcher.start()
        # ... application runs ...
        watcher.stop()
    """

    def __init__(self, raw_dir: Optional[Path] = None) -> None:
        self._raw_dir = raw_dir or _RAW_DIR
        self._raw_dir.mkdir(parents=True, exist_ok=True)

        self._q: queue.Queue = queue.Queue()
        self._log: List[IngestionLogEntry] = []
        self._lock = threading.Lock()
        self._observer = None
        self._worker: Optional[threading.Thread] = None
        self._running = False

        self._total_processed = 0
        self._total_errors = 0
        self._last_event_at: Optional[str] = None
        self._last_error: Optional[str] = None

    # ── Public API ─────────────────────────────────────────────────────────

    def start(self) -> None:
        """Start the file-system observer and the worker thread."""
        if self._running:
            return
        self._running = True

        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler

            handler = _KBEventHandler(self._q, self._add_log_detail)

            # Wrap our handler so watchdog calls the right methods
            class _WD(FileSystemEventHandler):
                def __init__(self, inner):
                    self._inner = inner

                def on_created(self, event):
                    self._inner.on_created(event)

                def on_modified(self, event):
                    self._inner.on_modified(event)

                def on_deleted(self, event):
                    self._inner.on_deleted(event)

                def on_moved(self, event):
                    self._inner.on_moved(event)

            self._observer = Observer()
            self._observer.schedule(_WD(handler), str(self._raw_dir), recursive=False)
            self._observer.start()
            logger.info("KBWatcher: observing {}", self._raw_dir)
        except ImportError:
            logger.warning("KBWatcher: watchdog not installed — file monitoring disabled")
            self._observer = None
        except Exception as exc:
            logger.warning("KBWatcher: could not start observer — {}", exc)
            self._observer = None

        self._worker = threading.Thread(
            target=self._worker_loop, daemon=True, name="kb-watcher-worker"
        )
        self._worker.start()

    def stop(self) -> None:
        """Stop the observer and worker."""
        self._running = False
        if self._observer:
            try:
                self._observer.stop()
                self._observer.join(timeout=5)
            except Exception:
                pass
        self._q.put(None)  # poison pill for worker
        if self._worker:
            self._worker.join(timeout=10)

    def queue_reindex(self, filename: str) -> bool:
        """Manually queue a single file for re-indexing."""
        target = self._raw_dir / filename
        if not target.exists():
            return False
        self._q.put(("reindex", target))
        self._append_log(IngestionLogEntry(
            timestamp=datetime.now().isoformat(),
            event="reindex",
            filename=filename,
            status="queued",
        ))
        return True

    def queue_full_refresh(self) -> int:
        """Queue all files in raw_dir for re-indexing. Returns queued count."""
        count = 0
        for f in self._raw_dir.iterdir():
            if f.suffix.lower() in SUPPORTED_EXTENSIONS:
                self._q.put(("reindex", f))
                count += 1
        if count:
            self._append_log(IngestionLogEntry(
                timestamp=datetime.now().isoformat(),
                event="reindex",
                filename="ALL",
                status="queued",
                detail=f"Full refresh: {count} files queued",
            ))
        return count

    def remove_document(self, filename: str) -> bool:
        """Remove a document from the knowledge base (sync, blocking)."""
        target = self._raw_dir / filename
        self._append_log(IngestionLogEntry(
            timestamp=datetime.now().isoformat(),
            event="deleted",
            filename=filename,
            status="processing",
        ))
        ok = _remove_single(target, lambda d: self._add_log_detail(d))
        status = "removed" if ok else "failed"
        self._append_log(IngestionLogEntry(
            timestamp=datetime.now().isoformat(),
            event="deleted",
            filename=filename,
            status=status,
        ))
        return ok

    def status(self) -> KBStatus:
        """Return current watcher status."""
        indexed = 0
        try:
            manifest_path = _STORE_DIR / "manifest.json"
            if manifest_path.exists():
                with open(manifest_path) as f:
                    data = json.load(f)
                indexed = len(data)
        except Exception:
            pass

        return KBStatus(
            watcher_running=self._running and self._observer is not None,
            monitored_path=str(self._raw_dir),
            queue_depth=self._q.qsize(),
            total_processed=self._total_processed,
            total_errors=self._total_errors,
            last_event_at=self._last_event_at,
            last_error=self._last_error,
            indexed_files=indexed,
        )

    def get_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return the last N ingestion log entries."""
        with self._lock:
            entries = list(self._log)
        return [e.to_dict() for e in entries[-limit:]]

    def list_documents(self) -> List[Dict[str, Any]]:
        """Return rich document list by scanning all store subdirectories.

        Reads every *.json file under data/store/json/<type>/ so that
        DBC, PNG/JPG, PDF and XLSX files are all represented — not just
        those registered in manifest.json.
        """
        result = []
        try:
            # Load manifest for extra metadata (checksum, file_size, stored_at)
            manifest: Dict[str, Any] = {}
            manifest_path = _STORE_DIR / "manifest.json"
            if manifest_path.exists():
                try:
                    with open(manifest_path) as f:
                        manifest = json.load(f)
                except Exception:
                    pass

            # Scan all type subdirectories under the store dir
            seen: set = set()
            for type_dir in sorted(_STORE_DIR.iterdir()):
                if not type_dir.is_dir():
                    continue
                doc_type = type_dir.name  # e.g. "pdf", "xlsx", "dbc", "png"

                for doc_path in sorted(type_dir.glob("*.json")):
                    stem = doc_path.stem  # e.g. "ServiceManual"
                    store_id = f"{doc_type}/{stem}"

                    if store_id in seen:
                        continue
                    seen.add(store_id)

                    # Determine the original filename (source)
                    ext_map = {
                        "pdf": ".pdf", "xlsx": ".xlsx", "xls": ".xls",
                        "dbc": ".dbc", "png": ".png", "jpg": ".jpg",
                        "jpeg": ".jpeg", "image": ".png",
                    }
                    ext = ext_map.get(doc_type, f".{doc_type}")
                    source = f"{stem}{ext}"

                    # Read stored JSON for chunk/node counts
                    chunks = 0
                    nodes = 0
                    edges = 0
                    try:
                        with open(doc_path, encoding="utf-8") as f:
                            doc_data = json.load(f)
                        rg = doc_data.get("relationship_graph", {}) or {}
                        nodes = len(rg.get("nodes", {}))
                        edges = len(rg.get("edges", []))
                        chunks = len(doc_data.get("chunks", []))
                        # Use source from stored data if available
                        stored_source = doc_data.get("source", "")
                        if stored_source:
                            source = stored_source
                    except Exception:
                        pass

                    # Merge manifest metadata
                    manifest_entry = manifest.get(store_id, {})

                    raw_file = self._raw_dir / source
                    file_size = manifest_entry.get("file_size") or (
                        raw_file.stat().st_size if raw_file.exists() else 0
                    )

                    result.append({
                        "filename": source,
                        "type": doc_type,
                        "status": "indexed",
                        "chunks": chunks,
                        "nodes": nodes,
                        "edges": edges,
                        "last_indexed": manifest_entry.get("stored_at", ""),
                        "checksum": manifest_entry.get("checksum", ""),
                        "file_size": file_size,
                        "store_id": store_id,
                        "file_exists": raw_file.exists(),
                    })

        except Exception as exc:
            logger.warning("KBWatcher.list_documents: {}", exc)
        return result


    # ── Internal ────────────────────────────────────────────────────────────

    def _worker_loop(self) -> None:
        while self._running:
            try:
                item = self._q.get(timeout=1.0)
            except queue.Empty:
                continue
            if item is None:  # poison pill
                break

            event_type, path = item
            filename = path.name
            t0 = time.monotonic()
            self._last_event_at = datetime.now().isoformat()

            self._append_log(IngestionLogEntry(
                timestamp=self._last_event_at,
                event=event_type,
                filename=filename,
                status="processing",
            ))

            if event_type in ("add", "modify", "reindex"):
                ok = _ingest_single(path, self._add_log_detail)
            elif event_type == "delete":
                ok = _remove_single(path, self._add_log_detail)
            else:
                ok = False

            elapsed = (time.monotonic() - t0) * 1000
            if ok:
                self._total_processed += 1
                status = "done"
            else:
                self._total_errors += 1
                self._last_error = f"{event_type} {filename} failed"
                status = "failed"

            self._append_log(IngestionLogEntry(
                timestamp=datetime.now().isoformat(),
                event=event_type,
                filename=filename,
                status=status,
                duration_ms=round(elapsed, 1),
            ))
            self._q.task_done()

    def _append_log(self, entry: IngestionLogEntry) -> None:
        with self._lock:
            self._log.append(entry)
            if len(self._log) > _MAX_LOG_ENTRIES:
                self._log = self._log[-_MAX_LOG_ENTRIES:]

    def _add_log_detail(self, detail: str) -> None:
        """Append a progress detail message to the last log entry."""
        with self._lock:
            if self._log:
                self._log[-1].detail = detail


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_watcher_instance: Optional[KBWatcher] = None


def get_kb_watcher() -> KBWatcher:
    """Return the application-level KBWatcher singleton."""
    global _watcher_instance
    if _watcher_instance is None:
        _watcher_instance = KBWatcher()
    return _watcher_instance
