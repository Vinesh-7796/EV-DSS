"""Chat endpoint — processes natural-language technician queries."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from services.ai_service import AIService, get_ai_service

router = APIRouter()


class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str = Field(..., min_length=1, max_length=32000)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=16000)
    conversation_id: Optional[str] = None
    history: List[ChatMessage] = Field(default_factory=list)
    stream: bool = False


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


class CitationInfo(BaseModel):
    text: str = ""
    document_id: str = ""
    page: Optional[int] = None
    section: Optional[str] = None
    is_valid: bool = False
    reason: str = ""


class ComponentScore(BaseModel):
    name: str = ""
    score: float = 0.0


class ConfidenceInfo(BaseModel):
    overall_score: float = 0.0
    level: str = "UNKNOWN"
    validation_status: str = "PENDING"
    component_scores: List[ComponentScore] = Field(default_factory=list)
    hallucination_detected: bool = False


class EntityItem(BaseModel):
    name: str = ""
    entity_type: str = ""
    is_valid: bool = False
    reason: str = ""


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


class ChatResponse(BaseModel):
    conversation_id: str
    response: str
    problem_summary: str = ""
    possible_causes: List[str] = Field(default_factory=list)
    inspection_steps: List[str] = Field(default_factory=list)
    recommended_actions: List[str] = Field(default_factory=list)
    related_components: List[str] = Field(default_factory=list)
    connectors: List[str] = Field(default_factory=list)
    fuses: List[str] = Field(default_factory=list)
    relays: List[str] = Field(default_factory=list)
    can_signals: List[str] = Field(default_factory=list)
    confidence: ConfidenceInfo = Field(default_factory=ConfidenceInfo)
    safety_warnings: List[str] = Field(default_factory=list)
    evidence: List[EvidenceItem] = Field(default_factory=list)
    citations: List[CitationInfo] = Field(default_factory=list)
    entities: List[EntityItem] = Field(default_factory=list)
    validation: ValidationInfo = Field(default_factory=ValidationInfo)
    processing_time_ms: float = 0.0


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    ai_service: AIService = Depends(get_ai_service),
):
    try:
        result = await ai_service.process_chat(
            message=request.message,
            conversation_id=request.conversation_id,
            history=[{"role": m.role, "content": m.content} for m in request.history],
        )
        return ChatResponse(**result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)[:500])
