"""Diagnostics endpoint — runs the full AI pipeline on a technician query."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from services.ai_service import AIService, get_ai_service

router = APIRouter()


class DiagnoseRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=16000)
    conversation_id: Optional[str] = None


class EvidenceItem(BaseModel):
    node_id: str = ""
    document: str = ""
    section: str = ""
    page: int = 0
    content: str = ""
    score: float = 0.0
    relationship: str = ""
    entity: str = ""
    validator: str = ""


class CitationItem(BaseModel):
    text: str = ""
    document_id: str = ""
    page: Optional[int] = None
    section: Optional[str] = None
    is_valid: bool = False
    reason: str = ""


class EntityItem(BaseModel):
    name: str = ""
    entity_type: str = ""
    is_valid: bool = False
    reason: str = ""


class ComponentScore(BaseModel):
    name: str = ""
    score: float = 0.0


class ConfidenceDetail(BaseModel):
    overall_score: float = 0.0
    level: str = "UNKNOWN"
    validation_status: str = "PENDING"
    component_scores: List[ComponentScore] = Field(default_factory=list)
    hallucination_detected: bool = False


class StageInfo(BaseModel):
    name: str = ""
    status: str = ""
    duration_ms: float = 0.0
    error: str = ""
    result_count: int = 0


class ValidationInfo(BaseModel):
    status: str = ""
    stages: List[StageInfo] = Field(default_factory=list)
    hallucination_summary: str = ""
    safety_rules_triggered: List[str] = Field(default_factory=list)


class DiagnoseResponse(BaseModel):
    conversation_id: str
    problem_summary: str = ""
    possible_causes: List[str] = Field(default_factory=list)
    inspection_steps: List[str] = Field(default_factory=list)
    recommended_actions: List[str] = Field(default_factory=list)
    confidence: ConfidenceDetail = Field(default_factory=ConfidenceDetail)
    safety_warnings: List[str] = Field(default_factory=list)
    evidence: List[EvidenceItem] = Field(default_factory=list)
    citations: List[CitationItem] = Field(default_factory=list)
    entities: List[EntityItem] = Field(default_factory=list)
    validation: ValidationInfo = Field(default_factory=ValidationInfo)
    processing_time_ms: float = 0.0


@router.post("", response_model=DiagnoseResponse)
async def diagnose(
    request: DiagnoseRequest,
    ai_service: AIService = Depends(get_ai_service),
):
    try:
        result = await ai_service.run_diagnosis(
            query=request.query,
            conversation_id=request.conversation_id,
        )
        return DiagnoseResponse(**result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)[:500])


@router.get("/statistics")
async def statistics():
    return {
        "total_diagnostics": 0,
        "average_confidence": 0.0,
        "status": "available",
    }
