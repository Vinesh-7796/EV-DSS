"""REST Endpoints for Diagnostic History & Reports.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel

from services.report_service import get_report_service
from services.ai_service import AIService, get_ai_service

router = APIRouter()

# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------

class RerunResponse(BaseModel):
    success: bool
    diagnostic_result: Dict[str, Any]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("")
def list_reports(query: Optional[str] = Query(None)) -> List[Dict[str, Any]]:
    """Retrieve all stored diagnostic reports. Optional filtering by query string."""
    service = get_report_service()
    all_reports = service.list_reports()
    
    if query:
        query_lower = query.lower()
        all_reports = [
            r for r in all_reports 
            if query_lower in r.get("query", "").lower() or query_lower in r.get("problem_summary", "").lower()
        ]
        
    return all_reports


@router.get("/{report_id}")
def get_report_detail(report_id: str) -> Dict[str, Any]:
    """Retrieve the full Markdown and structured diagnostic detail of a report."""
    service = get_report_service()
    detail = service.get_report_detail(report_id)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Report with ID '{report_id}' not found")
    return detail


@router.delete("/{report_id}")
def delete_report(report_id: str) -> Dict[str, Any]:
    """Delete a report from the local filesystem."""
    service = get_report_service()
    success = service.delete_report(report_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Report with ID '{report_id}' not found or could not be deleted")
    return {"success": True, "message": f"Successfully deleted report '{report_id}'"}


@router.get("/{report_id}/location")
def get_report_location(report_id: str) -> Dict[str, str]:
    """Get the physical location of the report on the host filesystem."""
    service = get_report_service()
    detail = service.get_report_detail(report_id)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Report with ID '{report_id}' not found")
    
    md_path = detail.get("metadata", {}).get("md_path", "")
    import os
    from pathlib import Path
    project_root = Path(__file__).resolve().parent.parent.parent
    absolute_path = str(project_root / md_path)
    
    return {
        "report_id": report_id,
        "relative_path": md_path,
        "absolute_path": absolute_path
    }


@router.post("/{report_id}/rerun")
async def rerun_report(
    report_id: str,
    ai_service: AIService = Depends(get_ai_service)
) -> RerunResponse:
    """Re-run a historical diagnosis using the same query against current knowledge base."""
    service = get_report_service()
    detail = service.get_report_detail(report_id)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Report with ID '{report_id}' not found")
        
    query = detail.get("metadata", {}).get("query", "")
    if not query:
        raise HTTPException(status_code=400, detail="Cannot rerun report - query text missing")
        
    try:
        # Run diagnosis again
        result = await ai_service.run_diagnosis(query=query)
        return RerunResponse(success=True, diagnostic_result=result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Diagnosis rerun failed: {str(exc)}")
