"""Report service — saves completed diagnoses to markdown reports under `Reports/YYYY/MM/`
and maintains an index for rapid retrieval, sorting, and history browsing.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

# Reports are saved at the project root under "Reports"
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_REPORTS_DIR = _PROJECT_ROOT / "Reports"

class ReportService:
    """Manages diagnostic report persistence, listing, and Markdown formatting."""

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        self.base_dir = base_dir or _REPORTS_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _sanitize_slug(self, query: str) -> str:
        """Create a filesystem-friendly name from the technician query."""
        slug = query.strip()[:30]
        slug = re.sub(r"[^\w\s-]", "", slug)
        slug = re.sub(r"[-\s]+", "_", slug)
        return slug or "Diagnosis"

    def save_report(self, query: str, result: Dict[str, Any]) -> str:
        """Format and write a markdown diagnostic report plus a metadata JSON sidecar.

        Returns:
            The relative path of the saved markdown report.
        """
        now = datetime.now()
        year_str = now.strftime("%Y")
        month_str = now.strftime("%m")
        time_slug = now.strftime("%Y-%m-%d_%H%M%S")
        
        query_slug = self._sanitize_slug(query)
        report_id = f"{query_slug}_{time_slug}"
        
        # Determine path: Reports/YYYY/MM/
        target_dir = self.base_dir / year_str / month_str
        target_dir.mkdir(parents=True, exist_ok=True)
        
        md_path = target_dir / f"{report_id}.md"
        json_path = target_dir / f"{report_id}.json"
        
        # Build Markdown content
        md_content = self.generate_markdown_report(query, result, now)
        
        # Build Metadata JSON for fast history loading
        metadata = {
            "id": report_id,
            "timestamp": now.isoformat(),
            "query": query,
            "problem_summary": result.get("problem_summary", ""),
            "confidence_score": result.get("confidence", {}).get("overall_score", 0.0),
            "confidence_level": result.get("confidence", {}).get("level", "UNKNOWN"),
            "model": result.get("active_model", "Unknown"),
            "processing_time_ms": result.get("processing_time_ms", 0.0),
            "md_path": str(md_path.relative_to(_PROJECT_ROOT)),
            "json_path": str(json_path.relative_to(_PROJECT_ROOT))
        }
        
        try:
            # Write MD file
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(md_content)
                
            # Write JSON metadata
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump({**result, "_metadata": metadata}, f, indent=2, ensure_ascii=False)
                
            logger.info("Saved diagnostic report: {}", md_path)
            return str(md_path.relative_to(_PROJECT_ROOT))
        except Exception as exc:
            logger.error("Failed to save report: {}", exc)
            raise exc

    def list_reports(self) -> List[Dict[str, Any]]:
        """Scan directory structure to list all diagnostic report metadata sidecars."""
        reports = []
        try:
            # Scan recursively for any *.json metadata files
            for json_file in self.base_dir.rglob("*.json"):
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    meta = data.get("_metadata", {})
                    if meta:
                        reports.append(meta)
                except Exception as exc:
                    logger.warning("Failed to parse report metadata sidecar {}: {}", json_file, exc)
        except Exception as exc:
            logger.error("Failed to list reports: {}", exc)
        
        # Sort by timestamp descending
        reports.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
        return reports

    def get_report_detail(self, report_id: str) -> Optional[Dict[str, Any]]:
        """Get full JSON and Markdown detail for a report by matching ID."""
        for json_file in self.base_dir.rglob("*.json"):
            if json_file.stem == report_id:
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    md_file = json_file.with_suffix(".md")
                    md_content = ""
                    if md_file.exists():
                        with open(md_file, "r", encoding="utf-8") as f:
                            md_content = f.read()
                            
                    return {
                        "metadata": data.get("_metadata", {}),
                        "diagnostic_result": data,
                        "markdown": md_content
                    }
                except Exception as exc:
                    logger.error("Failed to read details for report {}: {}", report_id, exc)
                    return None
        return None

    def delete_report(self, report_id: str) -> bool:
        """Find and delete the report markdown and json files."""
        deleted = False
        for json_file in self.base_dir.rglob("*.json"):
            if json_file.stem == report_id:
                try:
                    md_file = json_file.with_suffix(".md")
                    if md_file.exists():
                        md_file.unlink()
                    json_file.unlink()
                    logger.info("Deleted report files for ID: {}", report_id)
                    deleted = True
                except Exception as exc:
                    logger.error("Failed to delete report files for {}: {}", report_id, exc)
        return deleted

    def generate_markdown_report(self, query: str, result: Dict[str, Any], dt: datetime) -> str:
        """Create a beautifully formatted Markdown diagnostic report."""
        conf = result.get("confidence", {})
        val = result.get("validation", {})
        
        causes = "\n".join(f"- {c}" for c in result.get("possible_causes", []))
        steps = "\n".join(f"{i+1}. {s}" for i, s in enumerate(result.get("inspection_steps", [])))
        actions = "\n".join(f"- {a}" for a in result.get("recommended_actions", []))
        warnings = "\n".join(f"- ⚠️ **{w}**" for w in result.get("safety_warnings", []))
        
        retrieved_docs = set()
        for ev in result.get("evidence", []):
            if ev.get("document"):
                retrieved_docs.add(ev.get("document"))
        for cit in result.get("citations", []):
            if cit.get("document_id"):
                retrieved_docs.add(cit.get("document_id"))
        retrieved_docs_str = ", ".join(retrieved_docs) if retrieved_docs else "None"

        citations_list = "\n".join(
            f"- [{ 'VALID' if c.get('is_valid') else 'INVALID' }] {c.get('text')} (Reason: {c.get('reason', 'N/A')})"
            for c in result.get("citations", [])
        )

        scores_str = ""
        for score_item in conf.get("component_scores", []):
            scores_str += f"  - **{score_item.get('name')}**: {score_item.get('score', 0.0):.2f}\n"

        report_md = f"""# Diagnostic Report - {dt.strftime("%Y-%m-%d %H:%M:%S")}

## Query
> {query}

---

## Executive Summary
* **Problem Summary**: {result.get("problem_summary", "N/A")}
* **Confidence Level**: **{conf.get("level", "UNKNOWN")}** ({conf.get("overall_score", 0.0):.2f})
* **Validation Status**: `{conf.get("validation_status", "PENDING")}`

---

## Possible Causes
{causes or "None identified."}

## Recommended Inspection Steps
{steps or "None recommended."}

## Recommended Action Plan
{actions or "None recommended."}

---

## Safety & Compliance Warnings
{warnings or "No active safety warnings triggered."}

---

## Validation & Citations
### Retrieved Knowledge Documents
* {retrieved_docs_str}

### Citations Breakdown
{citations_list or "No citations parsed."}

### Confidence Score Breakdown
{scores_str or "N/A"}

---

## Runtime Metadata
* **Active Reasoning Model**: `{result.get("active_model", "Unknown")}`
* **Processing latency**: `{result.get("processing_time_ms", 0.0)} ms`
* **Validation status**: `{val.get("status", "N/A")}`
"""
        return report_md

_report_service_instance: Optional[ReportService] = None

def get_report_service() -> ReportService:
    global _report_service_instance
    if _report_service_instance is None:
        _report_service_instance = ReportService()
    return _report_service_instance
