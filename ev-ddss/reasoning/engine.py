"""Reasoning Engine — the top-level LLM orchestration layer.

Pipeline
────────

    Technician Query + StructuredContextPackage
    ↓
    Intent Classification
    ↓
    Context Optimization
    ↓
    Prompt Construction (+ JSON mode)
    ↓
    Template Selection
    ↓
    LLM Execution (generate / stream)
    ↓
    Response Parsing (fallback)
    ↓
    DiagnosticResponse

The engine performs reasoning exclusively on the supplied context.
It never retrieves documents, accesses databases, or performs OCR.

Profiling instrumentation added.
"""

import re
import time
from typing import Any, Dict, Generator, List, Optional

from backend.logger import logger
from reasoning.adapters.base_adapter import BaseLLMAdapter, LLMResponse, ModelInfo
from reasoning.adapters.ollama_adapter import OllamaAdapter
from reasoning.adapters.openai_adapter import OpenAICompatibleAdapter
from reasoning.adapters.vllm_adapter import VLLMAdapter
from reasoning.config import ReasoningConfig
from reasoning.context_optimizer import ContextOptimizer
from reasoning.intent_classifier import IntentClassifier, get_template_for_intent
from reasoning.models.diagnostic_response import DiagnosticResponse
from reasoning.prompt_builder import PromptBuilder
from reasoning.response_parser import ResponseParser
from reasoning.template_manager import TemplateManager
from reasoning.token_estimator import TokenEstimator

from retrieval.models import StructuredContextPackage


class ReasoningEngine:
    """LLM Orchestration Engine — transforms retrieved context into a
    structured ``DiagnosticResponse``.

    Usage::

        engine = ReasoningEngine()
        engine.initialize()
        response = engine.reason(query, context_package)
        print(response.problem_summary)
    """

    def __init__(
        self,
        config: Optional[ReasoningConfig] = None,
        adapter: Optional[BaseLLMAdapter] = None,
        intent_classifier: Optional[IntentClassifier] = None,
        context_optimizer: Optional[ContextOptimizer] = None,
        template_manager: Optional[TemplateManager] = None,
        prompt_builder: Optional[PromptBuilder] = None,
        response_parser: Optional[ResponseParser] = None,
        token_estimator: Optional[TokenEstimator] = None,
    ) -> None:
        self._config = config or ReasoningConfig().resolve()
        self._adapter = adapter
        self._intent_classifier = intent_classifier or IntentClassifier()
        self._token_estimator = token_estimator or TokenEstimator(self._config.model)
        self._context_optimizer = context_optimizer or ContextOptimizer(
            max_tokens=self._config.max_context_tokens,
            deduplicate=self._config.deduplicate_context,
            rank_by_score=self._config.rank_by_score,
            token_estimator=self._token_estimator,
        )
        self._template_manager = template_manager
        self._prompt_builder = prompt_builder
        self._response_parser = response_parser or ResponseParser(
            strict=self._config.strict_validation,
        )
        self._initialized = False
        self._last_response: Optional[LLMResponse] = None
        self._last_prompt: str = ""

    # ── Initialization ──────────────────────────

    def initialize(self) -> None:
        """Load adapter, templates, and validate configuration."""
        start = time.time()
        logger.info("ReasoningEngine initializing (runtime={}, model={})",
                     self._config.runtime, self._config.model)

        if self._adapter is None:
            self._adapter = self._create_adapter()

        if self._template_manager is None:
            self._template_manager = TemplateManager(
                template_dir=self._config.resolved_template_dir,
            )

        if self._prompt_builder is None:
            self._prompt_builder = PromptBuilder(
                template_manager=self._template_manager,
                system_prompt=self._config.system_prompt,
                json_mode_instruction=self._config.json_mode_system_instruction,
            )

        try:
            model_info = self._adapter.health_check()
            if model_info.healthy:
                logger.info("ReasoningEngine: adapter healthy (model={})", model_info.name)
            else:
                logger.warning("ReasoningEngine: {}", model_info.error)
        except Exception as exc:
            logger.warning("ReasoningEngine: adapter health check failed: {}", exc)

        self._initialized = True
        logger.info("ReasoningEngine initialized (runtime={}, model={}, templates={})",
                     self._config.runtime, self._config.model,
                     self._template_manager.list_templates())

    # ── Main API ────────────────────────────────

    def reason(
        self,
        query: str,
        context: StructuredContextPackage,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> DiagnosticResponse:
        """Run the full reasoning pipeline for a single query + context.

        Parameters
        ----------
        query : str
            The technician's natural-language query.
        context : StructuredContextPackage
            Retrieved context from the Hybrid Retrieval Engine.
        conversation_history : list of dict or None
            Optional conversation history for multi-turn dialogue.

        Returns
        -------
        DiagnosticResponse
            Structured diagnostic response.

        Raises
        ------
        RuntimeError
            If the engine is not initialized.
        """
        if not self._initialized:
            raise RuntimeError("ReasoningEngine not initialized. Call initialize() first.")

        overall_start = time.time()
        logger.info("ReasoningEngine: stage1_start - intent_classification")

        # 1. Intent classification
        intent_start = time.time()
        intent, matched_phrases = self._intent_classifier.classify(query)
        intent_time_ms = (time.time() - intent_start) * 1000
        logger.info("ReasoningEngine: intent={} (matched: {}) in %.0f ms",
                     intent.value, matched_phrases, intent_time_ms)

        # 2. Context optimization
        context_start = time.time()
        optimized = self._context_optimizer.optimize(context)
        context_time_ms = (time.time() - context_start) * 1000
        logger.info("ReasoningEngine: context optimized ({} results) in %.0f ms",
                     optimized.total_results, context_time_ms)

        # 3. Build context text
        context_text_start = time.time()
        context_text = self._prompt_builder.build_context_text(
            semantic_context=optimized.semantic_context,
            exact_matches=optimized.exact_matches,
            graph_context=optimized.graph_context,
            image_references=optimized.image_references,
        )
        context_text_time_ms = (time.time() - context_text_start) * 1000
        logger.info("ReasoningEngine: context text built in %.0f ms (%.0f chars)",
                     context_text_time_ms, len(context_text))

        # 4. Select template
        template_start = time.time()
        template_name = get_template_for_intent(intent, self._config.template_map)
        template_meta = self._template_manager.get_metadata(template_name)
        template_time_ms = (time.time() - template_start) * 1000
        logger.info("ReasoningEngine: template={} v{} for intent={} in %.0f ms",
                     template_name, template_meta.get("template_version", "?"), intent.value, template_time_ms)

        evidence_response = self._diagnostic_row_response_from_context(query, optimized, min_score=0.9)
        if evidence_response is not None:
            llm_response = LLMResponse(
                text="",
                success=True,
                model_used="structured-evidence",
                runtime_used="retrieval",
                generation_time_ms=0.0,
            )
            self._attach_metadata(evidence_response, llm_response, intent.value, template_name,
                                  template_meta, optimized, matched_phrases, overall_start, recovery=True)
            return evidence_response

        # 5. Determine JSON mode
        use_json_mode = self._config.json_mode and self._adapter.supports_json_mode

        # 6. Filter conversation history by config
        history = None
        if self._config.enable_history and conversation_history:
            history = conversation_history[-(self._config.max_history_turns * 2):]

        # 7. Build prompt
        prompt_start = time.time()
        prompt = self._prompt_builder.build(
            template_name=template_name,
            context_text=context_text,
            query=query,
            intent=intent.value,
            conversation_history=history,
            json_mode=use_json_mode,
        )
        self._last_prompt = prompt
        prompt_time_ms = (time.time() - prompt_start) * 1000
        logger.info("ReasoningEngine: prompt built in %.0f ms (%.0f chars)",
                     prompt_time_ms, len(prompt))

        # 8. Execute LLM
        llm_start = time.time()
        llm_response = self._adapter.generate(
            prompt,
            temperature=self._config.temperature,
            max_tokens=self._config.max_tokens,
            json_mode=use_json_mode,
        )
        self._last_response = llm_response
        llm_time_ms = (time.time() - llm_start) * 1000

        if not llm_response.success:
            logger.error("ReasoningEngine: LLM call failed: {}", llm_response.error)
            resp = (
                self._diagnostic_row_response_from_context(query, optimized, min_score=0.9)
                or self._fallback_response_from_context(query, llm_response.error, optimized, allow_generic=False)
                or self._fallback_response(query, llm_response.error)
            )
            self._attach_metadata(resp, llm_response, intent.value, template_name,
                                  template_meta, optimized, matched_phrases, overall_start, recovery=False)
            return resp

        logger.info("ReasoningEngine: LLM responded (tokens={}, {:.0f}ms)",
                     llm_response.total_tokens, llm_response.generation_time_ms)

        # 9. Parse response (fallback — JSON mode is primary enforcement)
        parse_start = time.time()
        parse_result = self._response_parser.parse(llm_response.text)
        recovery_used = parse_result.recovery_used
        parse_time_ms = (time.time() - parse_start) * 1000
        logger.info("ReasoningEngine: response parsed (success={}, recovery_used={}, error={}) in %.0f ms",
                     parse_result.success, recovery_used, parse_result.error, parse_time_ms)

        if not parse_result.success:
            logger.error("ReasoningEngine: response parsing failed: {}", parse_result.error)
            evidence_response = self._fallback_response_from_context(query, parse_result.error, optimized)
            if evidence_response is not None:
                self._attach_metadata(evidence_response, llm_response, intent.value, template_name,
                                      template_meta, optimized, matched_phrases, overall_start, recovery=True)
                return evidence_response

            if self._config.retry_on_parse_failure and self._config.max_retries > 0:
                for attempt in range(self._config.max_retries):
                    logger.info("ReasoningEngine: retry attempt {}/{}", attempt + 1, self._config.max_retries)
                    llm_response = self._adapter.generate(
                        self._build_retry_prompt(parse_result.error),
                        temperature=self._config.temperature + 0.1,
                        max_tokens=self._config.max_tokens,
                        json_mode=use_json_mode,
                    )
                    if llm_response.success:
                        parse_result = self._response_parser.parse(llm_response.text)
                        if parse_result.success:
                            recovery_used = True
                            break

            if not parse_result.success:
                resp = self._fallback_response(query, parse_result.error)
                self._attach_metadata(resp, llm_response, intent.value, template_name,
                                      template_meta, optimized, matched_phrases, overall_start, recovery=False)
                return resp

        # 10. Attach metadata
        response = parse_result.response
        if response is not None:
            self._attach_metadata(response, llm_response, intent.value, template_name,
                                  template_meta, optimized, matched_phrases, overall_start, recovery_used)

        if not response.citations:
            response.citations = optimized.citations[:10]

        total_time_ms = (time.time() - overall_start) * 1000
        logger.info("ReasoningEngine: complete ({}) in %.0f ms (overall: %.0f ms)",
                     response.summary(), total_time_ms)

        return response

    # ── Streaming ───────────────────────────────

    def stream_reason(
        self,
        query: str,
        context: StructuredContextPackage,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> Generator[str, None, None]:
        """Stream the LLM response token by token.

        Uses the same pipeline as ``reason()`` but returns a generator
        that yields content chunks as they are generated.
        """
        if not self._initialized:
            raise RuntimeError("ReasoningEngine not initialized. Call initialize() first.")

        intent, matched_phrases = self._intent_classifier.classify(query)
        optimized = self._context_optimizer.optimize(context)
        context_text = self._prompt_builder.build_context_text(
            semantic_context=optimized.semantic_context,
            exact_matches=optimized.exact_matches,
            graph_context=optimized.graph_context,
            image_references=optimized.image_references,
        )
        template_name = get_template_for_intent(intent, self._config.template_map)
        use_json_mode = self._config.json_mode and self._adapter.supports_json_mode

        history = None
        if self._config.enable_history and conversation_history:
            history = conversation_history[-(self._config.max_history_turns * 2):]

        prompt = self._prompt_builder.build(
            template_name=template_name,
            context_text=context_text,
            query=query,
            intent=intent.value,
            conversation_history=history,
            json_mode=use_json_mode,
        )
        self._last_prompt = prompt

        yield from self._adapter.stream_generate(
            prompt,
            temperature=self._config.temperature,
            max_tokens=self._config.max_tokens,
            json_mode=use_json_mode,
        )

    # ── Properties ──────────────────────────────

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    @property
    def config(self) -> ReasoningConfig:
        return self._config

    @property
    def last_prompt(self) -> str:
        return self._last_prompt

    @property
    def last_llm_response(self) -> Optional[LLMResponse]:
        return self._last_response

    # ── Internal ───────────────────────────────

    def _create_adapter(self) -> BaseLLMAdapter:
        runtime = self._config.runtime.lower()
        if runtime == "ollama":
            return OllamaAdapter(
                model=self._config.model,
                url=self._config.ollama_url,
                temperature=self._config.temperature,
                top_p=self._config.top_p,
                max_tokens=self._config.max_tokens,
                context_window=self._config.context_window,
                timeout_s=self._config.request_timeout_s,
            )
        elif runtime == "openai":
            return OpenAICompatibleAdapter(
                model=self._config.openai_model or self._config.model,
                url=self._config.openai_url,
                api_key=self._config.openai_api_key,
                temperature=self._config.temperature,
                top_p=self._config.top_p,
                max_tokens=self._config.max_tokens,
                context_window=self._config.context_window,
                timeout_s=self._config.request_timeout_s,
            )
        elif runtime == "vllm":
            return VLLMAdapter(
                model=self._config.vllm_model or self._config.model,
                url=self._config.vllm_url,
                temperature=self._config.temperature,
                max_tokens=self._config.max_tokens,
                context_window=self._config.context_window,
            )
        else:
            raise ValueError(
                f"Unsupported runtime '{runtime}'. Supported: ollama, openai, vllm"
            )

    def _build_retry_prompt(self, parse_error: str) -> str:
        return (
            f"{self._last_prompt}\n\n"
            f"[SYSTEM: Your previous response failed JSON validation. "
            f"Error: {parse_error}\n"
            f"Please respond ONLY with valid JSON matching the required schema. "
            f"Do not include markdown formatting or explanatory text.]"
        )

    def _fallback_response(self, query: str, error: str) -> DiagnosticResponse:
        return DiagnosticResponse(
            problem_summary=f"Unable to generate diagnostic response for: {query[:100]}",
            possible_causes=[f"Engine unavailable: {error[:200]}"],
            inspection_steps=["Check that the LLM service is running and configured correctly."],
            recommended_actions=["Verify configuration and service status."],
            referenced_entities=[],
            referenced_documents=[],
            reasoning_summary=f"LLM orchestration error: {error[:200]}",
            citations=[],
            metadata={"error": error, "fallback": True},
        )

    def _fallback_response_from_context(
        self,
        query: str,
        error: str,
        context: StructuredContextPackage,
        allow_generic: bool = True,
    ) -> Optional[DiagnosticResponse]:
        """Build a structured answer from retrieved evidence when LLM JSON parsing fails."""
        query_upper = query.upper()
        code_match = re.search(r"\b[PCBU][0-9A-F]{4}\b", query_upper)
        query_code = code_match.group(0) if code_match else ""

        all_results = context.all_results
        error_row = None
        for result in all_results:
            content = str(getattr(result, "content", ""))
            if "Worksheet: ErrorCodes" not in content:
                continue
            if query_code and f"Code: {query_code}" in content:
                error_row = result
                break
            if not query_code and query.lower() in content.lower():
                error_row = result
                break
        if error_row is None and not query_code:
            for result in all_results:
                content = str(getattr(result, "content", ""))
                if "Worksheet: ErrorCodes" in content and float(getattr(result, "score", 0.0) or 0.0) >= 0.9:
                    error_row = result
                    break

        if error_row is not None:
            fields = self._parse_semicolon_fields(str(error_row.content))
            code = fields.get("Code", query_code or query)
            description = fields.get("Description", code)
            causes = self._split_evidence_list(fields.get("Possible Cause", ""))
            steps = self._split_evidence_list(fields.get("Inspection Procedure", ""))
            connectors = self._split_evidence_list(fields.get("Related Connector", ""))
            fuses = self._split_evidence_list(fields.get("Related Fuse", ""))
            can_signals = self._split_evidence_list(fields.get("Related CAN Message", ""))
            sections = self._split_evidence_list(fields.get("Related Section", ""))

            actions = []
            safety_step = (
                "Before EV diagnostic work, check for live voltage before opening panels; "
                "ensure proper grounding before testing; verify coolant is neutralized; "
                "check battery management system status; verify charger is unplugged before repairs."
            )
            for cause in causes[:4]:
                actions.append(f"Inspect and correct {cause}.")
            if not actions:
                actions = ["Use the listed inspection procedure to isolate the failed component."]
            if self._is_safety_relevant(description, causes, steps):
                steps = [safety_step] + steps
                actions = [safety_step] + actions

            referenced_entities = [code] + connectors + fuses + can_signals
            referenced_documents = sorted({str(getattr(r, "source", "")) for r in all_results if getattr(r, "source", "")})

            return DiagnosticResponse(
                problem_summary=f"{code}: {description}",
                possible_causes=causes or ["Supporting evidence was retrieved, but no explicit cause list was present."],
                inspection_steps=steps or ["Review the retrieved service evidence for the applicable diagnostic procedure."],
                recommended_actions=actions,
                referenced_entities=[item for item in referenced_entities if item and item != "-"],
                referenced_documents=referenced_documents,
                reasoning_summary=(
                    "LLM output could not be parsed as valid JSON, so this response was built "
                    "directly from the highest-ranked retrieved ErrorCodes evidence row."
                ),
                citations=[error_row.to_citation()] + [r.to_citation() for r in all_results[:5] if r is not error_row],
                related_components=causes[:4],
                connectors=[item for item in connectors if item != "-"],
                fuses=[item for item in fuses if item != "-"],
                relays=[],
                can_signals=[item for item in can_signals if item != "-"],
                metadata={
                    "error": error,
                    "fallback": True,
                    "fallback_source": "retrieved_error_code_row",
                    "related_sections": sections,
                },
            )

        if allow_generic and all_results:
            top = all_results[0]
            return DiagnosticResponse(
                problem_summary=f"Retrieved engineering evidence for: {query}",
                possible_causes=[str(getattr(top, "content", ""))[:300]],
                inspection_steps=["Review the cited retrieved evidence and run the corresponding diagnostic checks."],
                recommended_actions=["Use the cited source material to continue diagnosis."],
                referenced_entities=[query],
                referenced_documents=sorted({str(getattr(r, "source", "")) for r in all_results if getattr(r, "source", "")}),
                reasoning_summary="LLM output could not be parsed as valid JSON; returned retrieved evidence summary.",
                citations=[r.to_citation() for r in all_results[:5]],
                metadata={"error": error, "fallback": True, "fallback_source": "retrieved_top_result"},
            )

        return None

    def _exact_dtc_response_from_context(
        self,
        query: str,
        context: StructuredContextPackage,
    ) -> Optional[DiagnosticResponse]:
        query_upper = query.upper().strip()
        if not re.fullmatch(r"[PCBU][0-9A-F]{4}", query_upper):
            return None
        return self._fallback_response_from_context(
            query=query,
            error="Exact diagnostic trouble code resolved from retrieved ErrorCodes evidence.",
            context=context,
            allow_generic=False,
        )

    def _diagnostic_row_response_from_context(
        self,
        query: str,
        context: StructuredContextPackage,
        min_score: float = 0.9,
    ) -> Optional[DiagnosticResponse]:
        if re.fullmatch(r"[PCBU][0-9A-F]{4}", query.upper().strip()):
            return self._exact_dtc_response_from_context(query, context)
        for result in context.all_results:
            content = str(getattr(result, "content", ""))
            if "Worksheet: ErrorCodes" in content and float(getattr(result, "score", 0.0) or 0.0) >= min_score:
                package = StructuredContextPackage(query=query, exact_matches=[result])
                return self._fallback_response_from_context(
                    query=query,
                    error="Natural-language symptom resolved from high-confidence ErrorCodes evidence.",
                    context=package,
                    allow_generic=False,
                )
        return None

    @staticmethod
    def _parse_semicolon_fields(content: str) -> Dict[str, str]:
        _, _, field_text = content.partition(": ")
        matches = list(re.finditer(r"(Code|Description|Severity|Possible Cause|Inspection Procedure|Related Connector|Related Fuse|Related CAN Message|Related Section):", field_text))
        fields: Dict[str, str] = {}
        for index, match in enumerate(matches):
            start = match.end()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(field_text)
            fields[match.group(1)] = field_text[start:end].strip(" ;")
        return fields

    @staticmethod
    def _split_evidence_list(value: str) -> List[str]:
        items = []
        for item in re.split(r";|,", value or ""):
            cleaned = item.strip()
            if cleaned:
                items.append(cleaned)
        return items

    @staticmethod
    def _is_safety_relevant(description: str, causes: List[str], steps: List[str]) -> bool:
        text = " ".join([description] + causes + steps).lower()
        return any(keyword in text for keyword in (
            "high voltage", "hv", "battery", "pack", "inverter", "contactor",
            "charger", "isolation", "coolant", "traction", "dc bus",
        ))

    def _attach_metadata(
        self,
        response: DiagnosticResponse,
        llm_response: LLMResponse,
        intent: str,
        template_name: str,
        template_meta: Dict[str, Any],
        optimized: StructuredContextPackage,
        matched_phrases: List[str],
        start: float,
        recovery: bool,
    ) -> None:
        elapsed_ms = (time.time() - start) * 1000.0
        response.metadata = {
            "model": llm_response.model_used,
            "runtime": llm_response.runtime_used,
            "intent": intent,
            "template_name": template_name,
            "template_version": template_meta.get("template_version", ""),
            "template_description": template_meta.get("description", ""),
            "context_nodes_used": optimized.total_results,
            "prompt_tokens": llm_response.prompt_tokens,
            "completion_tokens": llm_response.completion_tokens,
            "total_tokens": llm_response.total_tokens,
            "generation_time_ms": llm_response.generation_time_ms,
            "total_time_ms": round(elapsed_ms, 1),
            "parser_recovery": recovery,
            "matched_phrases": matched_phrases,
            "timestamp": time.time(),
        }

    def summary(self) -> str:
        return (
            f"ReasoningEngine(runtime={self._config.runtime}, "
            f"model={self._config.model}, "
            f"templates={self._template_manager.list_templates() if self._template_manager else '?'}, "
            f"initialized={self._initialized})"
        )
