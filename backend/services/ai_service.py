"""AIService — adapter between the FastAPI layer and the AI Core.

This service is ONLY an adapter.  It never implements AI logic.
All reasoning stays in the existing ev-ddss modules.
"""

import asyncio
import time
import uuid
from typing import Any, Dict, List, Optional

from config import get_settings
from reasoning.engine import ReasoningEngine
from reasoning.config import ReasoningConfig
from retrieval.engine import HybridRetrievalEngine
from retrieval.models import StructuredContextPackage
from validation.engine import ValidationEngine

settings = get_settings()


class AIService:
    """Orchestrates the AI Core pipeline: retrieve -> reason -> validate.

    Thread-safe and stateless per-request.  No AI logic lives here.
    """

    def __init__(self) -> None:
        self._reasoning_engine: Optional[ReasoningEngine] = None
        self._retrieval_engine: Optional[HybridRetrievalEngine] = None
        self._validation_engine: Optional[ValidationEngine] = None
        self._initialized = False

    async def initialize(self) -> None:
        if self._initialized:
            return
        loop = asyncio.get_running_loop()

        def _init_sync() -> None:
            cfg = ReasoningConfig().resolve()
            engine = ReasoningEngine(config=cfg)
            engine.initialize()
            retrieval = HybridRetrievalEngine()
            retrieval.initialize()
            validation = ValidationEngine()
            self._reasoning_engine = engine
            self._retrieval_engine = retrieval
            self._validation_engine = validation
            self._initialized = True

        await loop.run_in_executor(None, _init_sync)

    async def process_chat(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        await self.initialize()
        cid = conversation_id or str(uuid.uuid4())
        start = time.time()

        context = await self._retrieve(message)
        response = self._reasoning_engine.reason(
            query=message,
            context=context,
            conversation_history=history,
        )
        validated = self._validate(response, context)

        elapsed = (time.time() - start) * 1000.0

        cr = validated.confidence_results
        cb = cr.confidence_breakdown if cr else None
        report = validated.validation_report

        component_scores = []
        if cb:
            for key in ("evidence_coverage", "citation_validity", "retrieval_score",
                        "entity_validation", "relationship_validation", "consistency",
                        "hallucination_detection"):
                val = getattr(cb, key, 0.0)
                component_scores.append({"name": key, "score": val})

        stages = []
        if report and report.pipeline_stages:
            for s in report.pipeline_stages:
                stages.append({
                    "name": s.stage_name,
                    "status": s.status,
                    "duration_ms": s.duration_ms,
                    "error": s.error,
                    "result_count": s.result_count,
                })

        return {
            "conversation_id": cid,
            "response": response.problem_summary,
            "problem_summary": response.problem_summary,
            "possible_causes": response.possible_causes,
            "inspection_steps": response.inspection_steps,
            "recommended_actions": response.recommended_actions,
            "related_components": getattr(response, "related_components", []),
            "connectors": getattr(response, "connectors", []),
            "fuses": getattr(response, "fuses", []),
            "relays": getattr(response, "relays", []),
            "can_signals": getattr(response, "can_signals", []),
            "confidence": {
                "overall_score": cr.overall_score if cr else 0.0,
                "level": cr.confidence_level if cr else "UNKNOWN",
                "validation_status": cr.validation_status if cr else "PENDING",
                "component_scores": component_scores,
                "hallucination_detected": len(report.hallucination_results) > 0 if report else False,
            },
            "safety_warnings": self._extract_safety_warnings(validated),
            "evidence": self._extract_evidence(validated),
            "citations": self._extract_citations(validated),
            "entities": self._extract_entities(validated),
            "validation": {
                "status": validated.status,
                "stages": stages,
                "hallucination_summary": report.hallucination_summary if report else "",
                "safety_rules_triggered": report.safety_rules_triggered if report else [],
            },
            "processing_time_ms": round(elapsed, 1),
        }

    async def run_diagnosis(
        self,
        query: str,
        conversation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        await self.initialize()
        cid = conversation_id or str(uuid.uuid4())
        start = time.time()

        context = await self._retrieve(query)
        response = self._reasoning_engine.reason(query=query, context=context)
        validated = self._validate(response, context)

        elapsed = (time.time() - start) * 1000.0

        cr = validated.confidence_results
        cb = cr.confidence_breakdown if cr else None
        report = validated.validation_report
        vr = validated.validated_response

        component_scores = []
        if cb:
            for key in ("evidence_coverage", "citation_validity", "retrieval_score",
                        "entity_validation", "relationship_validation", "consistency",
                        "hallucination_detection"):
                val = getattr(cb, key, 0.0)
                component_scores.append({"name": key, "score": val})

        stages = []
        if report and report.pipeline_stages:
            for s in report.pipeline_stages:
                stages.append({
                    "name": s.stage_name,
                    "status": s.status,
                    "duration_ms": s.duration_ms,
                    "error": s.error,
                    "result_count": s.result_count,
                })

        return {
            "conversation_id": cid,
            "problem_summary": response.problem_summary,
            "possible_causes": response.possible_causes,
            "inspection_steps": response.inspection_steps,
            "recommended_actions": response.recommended_actions,
            "related_components": getattr(response, "related_components", []),
            "connectors": getattr(response, "connectors", []),
            "fuses": getattr(response, "fuses", []),
            "relays": getattr(response, "relays", []),
            "can_signals": getattr(response, "can_signals", []),
            "confidence": {
                "overall_score": cr.overall_score if cr else 0.0,
                "level": cr.confidence_level if cr else "UNKNOWN",
                "validation_status": cr.validation_status if cr else "PENDING",
                "component_scores": component_scores,
                "hallucination_detected": len(report.hallucination_results) > 0 if report else False,
            },
            "safety_warnings": self._extract_safety_warnings(validated),
            "evidence": self._extract_evidence(validated),
            "citations": self._extract_citations(validated),
            "entities": self._extract_entities(validated),
            "validation": {
                "status": validated.status,
                "stages": stages,
                "hallucination_summary": report.hallucination_summary if report else "",
                "safety_rules_triggered": report.safety_rules_triggered if report else [],
            },
            "processing_time_ms": round(elapsed, 1),
        }

    async def _retrieve(self, query: str) -> StructuredContextPackage:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, self._retrieval_engine.retrieve, query
        )

    def _validate(self, response, context: StructuredContextPackage):
        from validation.models.diagnostic_response import DiagnosticResponse as ValDiagnosticResponse
        val_input = ValDiagnosticResponse(
            problem_summary=response.problem_summary,
            possible_causes=response.possible_causes,
            inspection_steps=response.inspection_steps,
            recommended_actions=response.recommended_actions,
            citations=response.citations,
            metadata=response.metadata or {},
        )
        return self._validation_engine.validate(val_input, context)

    def _extract_safety_warnings(self, validated) -> List[str]:
        vr = validated.validated_response
        if hasattr(vr, "safety_warnings") and vr.safety_warnings:
            return vr.safety_warnings
        sr = validated.safety_results
        if sr and hasattr(sr, "missing_warnings"):
            return sr.missing_warnings
        return []

    def _extract_evidence(self, validated) -> List[Dict[str, Any]]:
        evidence = []
        if validated.evidence_results and hasattr(validated.evidence_results, "validated_claims"):
            for claim in validated.evidence_results.validated_claims:
                evidence.append({
                    "node_id": claim.evidence_ids[0] if claim.evidence_ids else "",
                    "document": "",
                    "section": "",
                    "page": 0,
                    "content": claim.claim[:500],
                    "score": 1.0 if claim.is_supported else 0.0,
                    "relationship": "",
                    "entity": "",
                    "validator": claim.validator,
                })
        return evidence

    def _extract_citations(self, validated) -> List[Dict[str, Any]]:
        citations = []
        if validated.citation_results and hasattr(validated.citation_results, "valid_citations"):
            for c in validated.citation_results.valid_citations:
                citations.append({
                    "text": self._clean_citation_text(self._get_field(c, "citation", "")),
                    "document_id": "",
                    "page": None,
                    "section": None,
                    "is_valid": self._get_field(c, "is_valid", True),
                    "reason": self._get_field(c, "reason", ""),
                })
            for c in validated.citation_results.invalid_citations:
                citations.append({
                    "text": self._clean_citation_text(self._get_field(c, "citation", "")),
                    "document_id": "",
                    "page": None,
                    "section": None,
                    "is_valid": self._get_field(c, "is_valid", False),
                    "reason": self._get_field(c, "reason", ""),
                })
        return citations

    def _extract_entities(self, validated) -> List[Dict[str, Any]]:
        entities = []
        if validated.entity_results:
            er = validated.entity_results
            attr_map = [
                (er.validated_entities, True),
                (er.missing_entities, False),
            ]
            for items, is_valid in attr_map:
                if items:
                    for e in items:
                        entities.append({
                            "name": getattr(e, "entity_name", str(e)),
                            "entity_type": getattr(e, "entity_type", ""),
                            "is_valid": is_valid,
                            "reason": getattr(e, "reason", ""),
                        })
        return entities

    @staticmethod
    def _get_field(item: Any, name: str, default: Any = None) -> Any:
        if isinstance(item, dict):
            return item.get(name, default)
        return getattr(item, name, default)

    @staticmethod
    def _clean_citation_text(text: Any) -> str:
        return str(text or "").replace("\u00c2\u00a7", "section ").replace("\u00a7", "section ")


_service_instance: Optional[AIService] = None


def get_ai_service() -> AIService:
    global _service_instance
    if _service_instance is None:
        _service_instance = AIService()
    return _service_instance
