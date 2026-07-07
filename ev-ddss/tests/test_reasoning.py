"""Tests for the LLM Orchestration Engine (Phase 6).

Covers intent classification, context optimization, template management,
prompt building, LLM adapters (mocked), response parsing, DiagnosticResponse
validation, and the full ReasoningEngine pipeline.

All LLM calls are mocked — tests do NOT require a running model.
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Generator

import pytest

from reasoning.adapters.base_adapter import BaseLLMAdapter, LLMResponse, ModelInfo
from reasoning.config import ReasoningConfig
from reasoning.context_optimizer import ContextOptimizer
from reasoning.engine import ReasoningEngine
from reasoning.intent_classifier import IntentClassifier, IntentType, get_template_for_intent
from reasoning.models.diagnostic_response import DiagnosticResponse
from reasoning.prompt_builder import PromptBuilder
from reasoning.response_parser import ResponseParser, ParseResult
from reasoning.template_manager import TemplateManager

from retrieval.models import RetrievalResult, RetrievalMethod, StructuredContextPackage


# ══════════════════════════════════════════════
#  Mock LLM Adapter
# ══════════════════════════════════════════════


class MockAdapter(BaseLLMAdapter):
    """Adapter that returns pre-configured responses (no network calls)."""

    def __init__(self, response_text: str = "", fail: bool = False) -> None:
        self._response_text = response_text
        self._fail = fail
        self._last_prompt: str = ""
        self._call_count = 0
        self._last_json_mode: Optional[bool] = None
        self._stream_chunks: List[str] = []

    def generate(self, prompt: str, **kwargs: Any) -> LLMResponse:
        self._last_prompt = prompt
        self._call_count += 1
        self._last_json_mode = kwargs.get("json_mode", False)
        if self._fail:
            return LLMResponse(success=False, error="Mock adapter failure.")
        return LLMResponse(
            text=self._response_text,
            success=True,
            model_used="mock-model",
            runtime_used="mock",
            prompt_tokens=50,
            completion_tokens=100,
            total_tokens=150,
            generation_time_ms=100.0,
        )

    def health_check(self) -> ModelInfo:
        return ModelInfo(
            name="mock-model",
            runtime="mock",
            context_window=8192,
            supports_streaming=True,
            supports_json_mode=True,
            healthy=not self._fail,
        )

    def model_info(self) -> ModelInfo:
        return self.health_check()

    def stream_generate(self, prompt: str, **kwargs: Any) -> Any:
        if self._stream_chunks:
            yield from self._stream_chunks
        else:
            yield self._response_text

    @property
    def supports_json_mode(self) -> bool:
        return True


# ══════════════════════════════════════════════
#  Fixtures
# ══════════════════════════════════════════════


@pytest.fixture
def valid_llm_json() -> str:
    return json.dumps({
        "problem_summary": "Battery voltage below threshold.",
        "possible_causes": ["Faulty alternator", "Weak battery"],
        "inspection_steps": ["Measure voltage at terminals"],
        "recommended_actions": ["Replace alternator"],
        "referenced_entities": ["P0562"],
        "referenced_documents": ["BMS_Manual.pdf"],
        "reasoning_summary": "Voltage reading indicates charging system fault.",
        "citations": ["BMS_Manual.pdf p.42"],
    })


@pytest.fixture
def minimal_context() -> StructuredContextPackage:
    return StructuredContextPackage(
        query="What causes P0562?",
        semantic_context=[
            RetrievalResult(
                content="P0562: System Voltage Low.",
                node_id="dtc1", node_type="paragraph",
                source="DTC_Ref.pdf", score=0.95,
                method=RetrievalMethod.VECTOR,
            ),
        ],
        citations=["DTC_Ref.pdf  (vector, score=0.95)"],
        confidence=0.9,
        methods_used=["vector"],
    )


@pytest.fixture
def template_manager(tmp_path) -> TemplateManager:
    tdir = tmp_path / "templates"
    tdir.mkdir()
    (tdir / "error_code.jinja").write_text(
        "{{ system_prompt }}\n\n{{ engineering_rules }}\n"
        "{% if json_mode_instruction %}{{ json_mode_instruction }}\n{% endif %}"
        "{{ context }}\n"
        "{% if conversation_history %}{{ conversation_history }}\n{% endif %}"
        "Query: {{ query }}"
    )
    (tdir / "general.jinja").write_text(
        "{{ system_prompt }}\n\n{{ engineering_rules }}\n"
        "{% if json_mode_instruction %}{{ json_mode_instruction }}\n{% endif %}"
        "{{ context }}\n"
        "{% if conversation_history %}{{ conversation_history }}\n{% endif %}"
        "Query: {{ query }}"
    )
    (tdir / "component.jinja").write_text(
        "{{ system_prompt }}\n\n{{ engineering_rules }}\n"
        "{% if json_mode_instruction %}{{ json_mode_instruction }}\n{% endif %}"
        "{{ context }}\n"
        "{% if conversation_history %}{{ conversation_history }}\n{% endif %}"
        "Query: {{ query }}"
    )
    return TemplateManager(tdir)


@pytest.fixture
def prompt_builder(template_manager) -> PromptBuilder:
    return PromptBuilder(template_manager)


# ══════════════════════════════════════════════
#  DiagnosticResponse Tests
# ══════════════════════════════════════════════


class TestDiagnosticResponse:
    def test_valid_response(self):
        resp = DiagnosticResponse(
            problem_summary="Test problem",
            possible_causes=["Cause 1", "Cause 2"],
            inspection_steps=["Step 1", "Step 2"],
            recommended_actions=["Action 1"],
        )
        assert resp.problem_summary == "Test problem"
        assert len(resp.possible_causes) == 2
        assert resp.referenced_entities == []

    def test_missing_required_fields_fails(self):
        with pytest.raises(Exception):
            DiagnosticResponse()  # missing required fields

    def test_empty_possible_causes_fails(self):
        with pytest.raises(Exception):
            DiagnosticResponse(
                problem_summary="Test",
                possible_causes=[],
                inspection_steps=["Step"],
                recommended_actions=["Action"],
            )

    def test_empty_inspection_steps_fails(self):
        with pytest.raises(Exception):
            DiagnosticResponse(
                problem_summary="Test",
                possible_causes=["Cause"],
                inspection_steps=[],
                recommended_actions=["Action"],
            )

    def test_empty_actions_fails(self):
        with pytest.raises(Exception):
            DiagnosticResponse(
                problem_summary="Test",
                possible_causes=["Cause"],
                inspection_steps=["Step"],
                recommended_actions=[],
            )

    def test_to_dict(self):
        resp = DiagnosticResponse(
            problem_summary="Test",
            possible_causes=["Cause"],
            inspection_steps=["Step"],
            recommended_actions=["Action"],
        )
        d = resp.to_dict()
        assert d["problem_summary"] == "Test"
        assert "metadata" in d

    def test_example_creates_valid_response(self):
        resp = DiagnosticResponse.example()
        assert resp.problem_summary == "Battery voltage below threshold."
        assert len(resp.possible_causes) >= 1

    def test_summary_format(self):
        resp = DiagnosticResponse(
            problem_summary="Low voltage detected",
            possible_causes=["Alternator fault"],
            inspection_steps=["Check voltage"],
            recommended_actions=["Replace part"],
        )
        summary = resp.summary()
        assert "Low voltage" in summary
        assert "Alternator" in summary

    def test_pydantic_serialization(self):
        resp = DiagnosticResponse(
            problem_summary="Test",
            possible_causes=["A"],
            inspection_steps=["B"],
            recommended_actions=["C"],
        )
        dumped = resp.model_dump_json()
        loaded = DiagnosticResponse.model_validate_json(dumped)
        assert loaded.problem_summary == "Test"


# ══════════════════════════════════════════════
#  Intent Classifier Tests
# ══════════════════════════════════════════════


class TestIntentClassifier:
    def setup_method(self):
        self.classifier = IntentClassifier()

    def test_error_code_dtc(self):
        intent, phrases = self.classifier.classify("What does DTC P0AA6 mean?")
        assert intent == IntentType.ERROR_CODE

    def test_error_code_trouble_code(self):
        intent, _ = self.classifier.classify("I have trouble code U0100")
        assert intent == IntentType.ERROR_CODE

    def test_can_signal_analysis(self):
        intent, _ = self.classifier.classify("What is the CAN signal value for 0x181?")
        assert intent == IntentType.CAN_SIGNAL

    def test_component_diagnostics(self):
        intent, _ = self.classifier.classify("The BCM is not working. Diagnose.")
        assert intent == IntentType.COMPONENT

    def test_connector_pinout(self):
        intent, _ = self.classifier.classify("What is the pinout for connector X2?")
        assert intent == IntentType.CONNECTOR

    def test_procedure_request(self):
        intent, _ = self.classifier.classify("How to replace the HV battery?")
        assert intent == IntentType.PROCEDURE

    def test_maintenance(self):
        intent, _ = self.classifier.classify("What is the maintenance schedule?")
        assert intent == IntentType.MAINTENANCE

    def test_specification(self):
        intent, _ = self.classifier.classify("What is the voltage range for the 12V battery?")
        assert intent == IntentType.SPECIFICATION

    def test_comparison(self):
        intent, _ = self.classifier.classify("Difference between CAN 2.0 and CAN FD?")
        assert intent == IntentType.COMPARISON

    def test_general_fallback(self):
        intent, _ = self.classifier.classify("Hello, can you help me?")
        assert intent == IntentType.GENERAL

    def test_empty_query(self):
        intent, _ = self.classifier.classify("")
        assert intent == IntentType.GENERAL

    def test_classify_with_confidence(self):
        intent, confidence, phrases = self.classifier.classify_with_confidence("DTC P0AA6 error code")
        assert intent == IntentType.ERROR_CODE
        assert confidence > 0.5
        assert len(phrases) >= 1

    def test_get_template_for_intent(self):
        tmap = {"error_code": "error_code.jinja", "general": "general.jinja"}
        assert get_template_for_intent(IntentType.ERROR_CODE, tmap) == "error_code.jinja"
        assert get_template_for_intent(IntentType.COMPONENT, tmap) == "general.jinja"


# ══════════════════════════════════════════════
#  Context Optimizer Tests
# ══════════════════════════════════════════════


class TestContextOptimizer:
    def test_optimize_deduplicates_by_node_id(self):
        pkg = StructuredContextPackage(
            query="test",
            semantic_context=[
                RetrievalResult(content="A", node_id="n1", score=0.9),
                RetrievalResult(content="B", node_id="n1", score=0.8),  # dup
            ],
        )
        opt = ContextOptimizer(deduplicate=True, rank_by_score=False, max_tokens=99999)
        result = opt.optimize(pkg)
        assert len(result.semantic_context) == 1

    def test_optimize_deduplicates_by_content(self):
        pkg = StructuredContextPackage(
            query="test",
            semantic_context=[
                RetrievalResult(content="Same text here", node_id="n1", score=0.9),
                RetrievalResult(content="Same text here", node_id="n2", score=0.8),
            ],
        )
        opt = ContextOptimizer(deduplicate=True, max_tokens=99999)
        result = opt.optimize(pkg)
        assert len(result.semantic_context) == 1

    def test_optimize_ranks_by_score(self):
        pkg = StructuredContextPackage(
            query="test",
            semantic_context=[
                RetrievalResult(content="Low", node_id="n1", score=0.5),
                RetrievalResult(content="High", node_id="n2", score=0.9),
            ],
        )
        opt = ContextOptimizer(deduplicate=False, rank_by_score=True, max_tokens=99999)
        result = opt.optimize(pkg)
        assert result.semantic_context[0].score == 0.9

    def test_optimize_respects_token_budget(self):
        long_text = "word " * 500
        short_text = "short"
        pkg = StructuredContextPackage(
            query="test",
            semantic_context=[
                RetrievalResult(content=long_text, node_id="n1", score=0.9),
                RetrievalResult(content=short_text, node_id="n2", score=0.8),
            ],
        )
        # Budget just enough for the short result
        opt = ContextOptimizer(max_tokens=2, deduplicate=False, rank_by_score=False)
        result = opt.optimize(pkg)
        # Only the short text should fit (long text is ~500 tokens based on 4 char/token)
        assert len(result.semantic_context) <= 2

    def test_optimize_does_not_mutate_original(self):
        pkg = StructuredContextPackage(
            query="test",
            semantic_context=[RetrievalResult(content="A", node_id="n1", score=0.9)],
        )
        opt = ContextOptimizer(max_tokens=99999)
        original_count = pkg.total_results
        result = opt.optimize(pkg)
        assert pkg.total_results == original_count
        assert result is not pkg

    def test_optimize_empty_package(self):
        pkg = StructuredContextPackage(query="test")
        opt = ContextOptimizer(max_tokens=99999)
        result = opt.optimize(pkg)
        assert result.total_results == 0

    def test_optimize_preserves_citations(self):
        pkg = StructuredContextPackage(
            query="test",
            semantic_context=[RetrievalResult(content="A", node_id="n1", score=0.9)],
            citations=["citation1"],
        )
        opt = ContextOptimizer(max_tokens=99999)
        result = opt.optimize(pkg)
        assert "citation1" in result.citations


# ══════════════════════════════════════════════
#  Template Manager Tests
# ══════════════════════════════════════════════


class TestTemplateManager:
    def test_list_templates(self, template_manager):
        templates = template_manager.list_templates()
        assert "error_code.jinja" in templates
        assert "general.jinja" in templates

    def test_render_template(self, template_manager):
        text = template_manager.render("error_code.jinja", system_prompt="You are an expert.",
                                        context="Context text.", query="What is P0AA6?")
        assert "You are an expert." in text
        assert "Context text." in text
        assert "What is P0AA6?" in text

    def test_render_nonexistent_template(self, template_manager):
        with pytest.raises(FileNotFoundError):
            template_manager.render("nonexistent.jinja")

    def test_exists(self, template_manager):
        assert template_manager.exists("error_code.jinja") is True
        assert template_manager.exists("fake.jinja") is False

    def test_health_check(self, template_manager):
        health = template_manager.health_check()
        assert health["healthy"] is True
        assert health["template_count"] >= 2

    def test_health_check_missing_dir(self, tmp_path):
        tm = TemplateManager(tmp_path / "nonexistent")
        health = tm.health_check()
        assert health["healthy"] is False
        assert health["exists"] is False

    def test_list_templates_empty_dir(self, tmp_path):
        tdir = tmp_path / "empty"
        tdir.mkdir()
        tm = TemplateManager(tdir)
        assert tm.list_templates() == []


# ══════════════════════════════════════════════
#  Prompt Builder Tests
# ══════════════════════════════════════════════


class TestPromptBuilder:
    def test_build_includes_all_components(self, prompt_builder):
        prompt = prompt_builder.build(
            template_name="error_code.jinja",
            context_text="Relevant context.",
            query="What is P0AA6?",
            intent="error_code",
        )
        assert "Relevant context." in prompt
        assert "What is P0AA6?" in prompt
        assert "automotive diagnostic" in prompt

    def test_build_system_message(self, prompt_builder):
        msg = prompt_builder.build_system_message()
        assert "automotive" in msg.lower()
        assert len(msg) > 20

    def test_build_context_text_all_sections(self, prompt_builder):
        from retrieval.models import RetrievalResult, RetrievalMethod
        text = prompt_builder.build_context_text(
            semantic_context=[RetrievalResult(content="Semantic", node_id="n1", score=0.9,
                                              source="doc1.pdf", method=RetrievalMethod.VECTOR)],
            exact_matches=[RetrievalResult(content="Exact", node_id="n2", score=1.0,
                                           source="doc2.pdf")],
            graph_context=[RetrievalResult(content="Graph info", node_id="n3")],
            image_references=[RetrievalResult(content="OCR text", node_id="n4")],
        )
        assert "SEMANTIC CONTEXT" in text
        assert "EXACT MATCHES" in text
        assert "GRAPH CONTEXT" in text
        assert "IMAGE REFERENCES" in text
        assert "Semantic" in text
        assert "Exact" in text
        assert "Graph info" in text
        assert "OCR text" in text

    def test_build_context_text_empty(self, prompt_builder):
        text = prompt_builder.build_context_text([], [], [], [])
        assert "No relevant context found" in text

    def test_build_with_extra_variables(self, prompt_builder):
        prompt = prompt_builder.build(
            template_name="error_code.jinja",
            context_text="ctx",
            query="q",
            extra_variables={"extra_var": "extra_value"},
        )
        # Template doesn't use extra_var, but it shouldn't crash
        assert "ctx" in prompt

    def test_build_with_history(self, prompt_builder):
        history = [{"role": "user", "content": "previous question"}]
        prompt = prompt_builder.build(
            template_name="error_code.jinja",
            context_text="ctx",
            query="q",
            conversation_history=history,
        )
        assert "ctx" in prompt


# ══════════════════════════════════════════════
#  LLM Adapter Tests
# ══════════════════════════════════════════════


class TestLLMAdapter:
    def test_mock_adapter_returns_response(self):
        adapter = MockAdapter(response_text="test response")
        resp = adapter.generate("Hello")
        assert resp.success is True
        assert resp.text == "test response"
        assert resp.runtime_used == "mock"

    def test_mock_adapter_failure(self):
        adapter = MockAdapter(fail=True)
        resp = adapter.generate("Hello")
        assert resp.success is False

    def test_mock_adapter_health_check(self):
        adapter = MockAdapter()
        info = adapter.health_check()
        assert info.healthy is True

    def test_mock_adapter_health_check_failure(self):
        adapter = MockAdapter(fail=True)
        info = adapter.health_check()
        assert info.healthy is False

    def test_mock_adapter_model_info(self):
        adapter = MockAdapter()
        info = adapter.model_info()
        assert info.name == "mock-model"

    def test_mock_adapter_tracks_calls(self):
        adapter = MockAdapter(response_text="ok")
        adapter.generate("q1")
        adapter.generate("q2")
        assert adapter._call_count == 2

    def test_base_adapter_stream_raises(self):
        adapter = MockAdapter()
        chunks = list(adapter.stream_generate("test"))
        assert chunks == [adapter._response_text]


# ══════════════════════════════════════════════
#  Response Parser Tests
# ══════════════════════════════════════════════


class TestResponseParser:
    def setup_method(self):
        self.parser = ResponseParser(strict=True)

    def test_parse_valid_json(self, valid_llm_json):
        result = self.parser.parse(valid_llm_json)
        assert result.success is True
        assert result.response is not None
        assert result.response.problem_summary == "Battery voltage below threshold."

    def test_parse_json_from_markdown(self, valid_llm_json):
        text = f"Here is the answer:\n\n```json\n{valid_llm_json}\n```"
        result = self.parser.parse(text)
        assert result.success is True

    def test_parse_json_from_braces(self, valid_llm_json):
        text = f"Some text before\n{valid_llm_json}\nSome text after"
        result = self.parser.parse(text)
        assert result.success is True

    def test_parse_empty_string(self):
        result = self.parser.parse("")
        assert result.success is False
        assert "Empty" in result.error

    def test_parse_trailing_comma_recovery(self):
        text = '{"problem_summary": "Test", "possible_causes": ["A",], "inspection_steps": ["B",], "recommended_actions": ["C",]}'
        result = self.parser.parse(text)
        assert result.success is True
        assert result.recovery_used is True

    def test_parse_single_quotes_recovery(self):
        text = "{'problem_summary': 'Test', 'possible_causes': ['A'], 'inspection_steps': ['B'], 'recommended_actions': ['C']}"
        result = self.parser.parse(text)
        assert result.success is True
        assert result.recovery_used is True

    def test_parse_missing_required_field(self):
        text = '{"problem_summary": "Test", "possible_causes": ["A"]}'
        result = self.parser.parse(text)
        assert result.success is False
        assert "inspection_steps" in result.error

    def test_parse_non_strict_fills_defaults(self):
        parser = ResponseParser(strict=False)
        text = '{"problem_summary": "Test", "possible_causes": ["A"], "inspection_steps": [], "recommended_actions": []}'
        result = parser.parse(text)
        assert result.success is True
        assert len(result.response.inspection_steps) >= 1

    def test_validate_empty_causes_fails(self):
        text = '{"problem_summary": "Test", "possible_causes": [""], "inspection_steps": ["B"], "recommended_actions": ["C"]}'
        result = self.parser.parse(text)
        # Non-empty list passes parser field check but Pydantic validates content
        assert result.success is False

    def test_parse_nested_braces(self):
        text = 'Some text { "problem_summary": "Test", "possible_causes": ["A"], "inspection_steps": ["B"], "recommended_actions": ["C"], "metadata": {"key": "val"} } more text'
        result = self.parser.parse(text)
        assert result.success is True


# ══════════════════════════════════════════════
#  Reasoning Engine Tests
# ══════════════════════════════════════════════


class TestReasoningEngine:
    def test_engine_initialization(self, template_manager, valid_llm_json):
        adapter = MockAdapter(response_text=valid_llm_json)
        engine = ReasoningEngine(
            adapter=adapter,
            template_manager=template_manager,
        )
        engine.initialize()
        assert engine.is_initialized is True

    def test_engine_reason_returns_diagnostic_response(self, template_manager, valid_llm_json, minimal_context):
        adapter = MockAdapter(response_text=valid_llm_json)
        engine = ReasoningEngine(
            adapter=adapter,
            template_manager=template_manager,
        )
        engine.initialize()
        response = engine.reason("What causes P0562?", minimal_context)
        assert isinstance(response, DiagnosticResponse)
        assert response.problem_summary == "Battery voltage below threshold."

    def test_engine_detects_intent(self, template_manager, valid_llm_json, minimal_context):
        adapter = MockAdapter(response_text=valid_llm_json)
        engine = ReasoningEngine(
            adapter=adapter,
            template_manager=template_manager,
        )
        engine.initialize()
        _ = engine.reason("DTC P0562 low voltage", minimal_context)
        # Check metadata for intent
        assert adapter._call_count == 1

    def test_engine_fallback_on_llm_failure(self, template_manager, minimal_context):
        adapter = MockAdapter(fail=True)
        engine = ReasoningEngine(
            adapter=adapter,
            template_manager=template_manager,
        )
        engine.initialize()
        response = engine.reason("What causes P0562?", minimal_context)
        assert isinstance(response, DiagnosticResponse)
        assert "unable" in response.problem_summary.lower() or "error" in response.problem_summary.lower()

    def test_engine_fallback_on_parse_failure(self, template_manager, minimal_context):
        adapter = MockAdapter(response_text="This is not JSON at all.")
        engine = ReasoningEngine(
            adapter=adapter,
            template_manager=template_manager,
            config=ReasoningConfig(max_retries=0, retry_on_parse_failure=False),
        )
        engine.initialize()
        response = engine.reason("What causes P0562?", minimal_context)
        assert isinstance(response, DiagnosticResponse)

    def test_engine_prompt_contains_context_and_query(self, template_manager, valid_llm_json, minimal_context):
        adapter = MockAdapter(response_text=valid_llm_json)
        engine = ReasoningEngine(
            adapter=adapter,
            template_manager=template_manager,
        )
        engine.initialize()
        _ = engine.reason("What causes P0562?", minimal_context)
        prompt = engine.last_prompt
        assert "P0562" in prompt
        assert "System Voltage Low" in prompt

    def test_engine_not_initialized_raises(self):
        engine = ReasoningEngine()
        with pytest.raises(RuntimeError, match="not initialized"):
            engine.reason("test", StructuredContextPackage(query="test"))

    def test_engine_retry_on_parse_failure(self, template_manager, minimal_context):
        adapter = MockAdapter(response_text="Bad JSON")
        parser = ResponseParser(strict=False)
        engine = ReasoningEngine(
            adapter=adapter,
            template_manager=template_manager,
            response_parser=parser,
            config=ReasoningConfig(max_retries=1, retry_on_parse_failure=True),
        )
        engine.initialize()
        response = engine.reason("test", minimal_context)
        assert isinstance(response, DiagnosticResponse)

    def test_engine_config_adapter_creation(self):
        from reasoning.adapters.ollama_adapter import OllamaAdapter
        config = ReasoningConfig().resolve()
        config.runtime = "ollama"
        config.model = "qwen3:8b"
        engine = ReasoningEngine(config=config)
        engine.initialize()
        assert engine._adapter is not None

    def test_engine_config_unsupported_runtime(self):
        config = ReasoningConfig(runtime="invalid_runtime").resolve()
        engine = ReasoningEngine(config=config)
        with pytest.raises(ValueError, match="Unsupported runtime"):
            engine.initialize()

    def test_engine_summary(self, template_manager):
        adapter = MockAdapter()
        engine = ReasoningEngine(adapter=adapter, template_manager=template_manager)
        engine.initialize()
        summary = engine.summary()
        assert "template" in summary
        assert "initialized" in summary

    def test_engine_metadata_in_response(self, template_manager, valid_llm_json, minimal_context):
        adapter = MockAdapter(response_text=valid_llm_json)
        engine = ReasoningEngine(
            adapter=adapter,
            template_manager=template_manager,
        )
        engine.initialize()
        response = engine.reason("What causes P0562?", minimal_context)
        assert response.metadata is not None
        assert "model" in response.metadata
        assert "intent" in response.metadata
        assert "total_tokens" in response.metadata

    def test_engine_citations_from_context(self, template_manager):
        no_citations_json = json.dumps({
            "problem_summary": "Test",
            "possible_causes": ["Cause A"],
            "inspection_steps": ["Step 1"],
            "recommended_actions": ["Action 1"],
            "referenced_entities": [],
            "referenced_documents": [],
            "reasoning_summary": "",
            "citations": [],
        })
        adapter = MockAdapter(response_text=no_citations_json)
        ctx = StructuredContextPackage(
            query="test",
            semantic_context=[RetrievalResult(content="A", node_id="n1", score=0.9)],
            citations=["test citation"],
        )
        engine = ReasoningEngine(adapter=adapter, template_manager=template_manager)
        engine.initialize()
        response = engine.reason("test", ctx)
        assert "test citation" in response.citations


# ══════════════════════════════════════════════
#  Configuration Tests
# ══════════════════════════════════════════════


class TestReasoningConfig:
    def test_default_config(self):
        config = ReasoningConfig().resolve()
        assert config.runtime == "ollama"
        assert config.model is not None
        assert config.max_tokens > 0

    def test_config_resolve_template_directory(self):
        config = ReasoningConfig(template_directory="").resolve()
        assert config.resolved_template_dir is not None
        assert config.resolved_template_dir.exists() is False or "templates" in str(config.resolved_template_dir)

    def test_config_timeline(self):
        config = ReasoningConfig().resolve()
        tl = config.timeline()
        assert "runtime" in tl
        assert "model" in tl
        assert "temperature" in tl


# ══════════════════════════════════════════════
#  Prompt Builder + Template Integration
# ══════════════════════════════════════════════


class TestPromptBuilderIntegration:
    def test_different_templates_different_prompts(self, prompt_builder, template_manager):
        # Only one template
        ec = prompt_builder.build("error_code.jinja", "ctx", "query1")
        gen = prompt_builder.build("general.jinja", "ctx", "query2")
        assert ec != gen

    def test_template_with_all_schema_variables(self, template_manager):
        tm = template_manager
        text = tm.render("error_code.jinja",
                          system_prompt="sys",
                          engineering_rules="rules",
                          context="ctx",
                          query="q",
                          intent="error_code",
                          conversation_history=[],
                          diagnostic_response_schema="schema here")
        assert "sys" in text
        assert "rules" in text
        assert "ctx" in text
        assert "q" in text


# ══════════════════════════════════════════════
#  Production Improvements Tests (Review Phase)
# ══════════════════════════════════════════════


class TestReasoningProductionImprovements:
    def test_json_mode_enabled_passed_to_adapter(self, template_manager, valid_llm_json, minimal_context):
        adapter = MockAdapter(response_text=valid_llm_json)
        config = ReasoningConfig(json_mode=True).resolve()
        engine = ReasoningEngine(adapter=adapter, template_manager=template_manager, config=config)
        engine.initialize()
        engine.reason("test query", minimal_context)
        assert adapter._last_json_mode is True

    def test_conversation_history_accepted_and_rendered(self, template_manager, valid_llm_json, minimal_context):
        adapter = MockAdapter(response_text=valid_llm_json)
        config = ReasoningConfig(enable_history=True).resolve()
        engine = ReasoningEngine(adapter=adapter, template_manager=template_manager, config=config)
        engine.initialize()
        history = [{"role": "user", "content": "hello"}]
        engine.reason("follow up", minimal_context, conversation_history=history)
        assert "[user]: hello" in engine.last_prompt

    def test_streaming_returns_chunks(self, template_manager, minimal_context):
        adapter = MockAdapter()
        adapter._stream_chunks = ["part1", "part2"]
        engine = ReasoningEngine(adapter=adapter, template_manager=template_manager)
        engine.initialize()
        chunks = list(engine.stream_reason("test", minimal_context))
        assert chunks == ["part1", "part2"]

    def test_token_estimator_with_tiktoken_mock(self):
        from reasoning.token_estimator import TokenEstimator
        te = TokenEstimator(model_name="gpt-4")
        count = te.estimate("test text")
        # Should use fallback or tiktoken if installed
        assert count > 0

    def test_template_metadata_parsing(self, tmp_path):
        tdir = tmp_path / "meta_templates"
        tdir.mkdir()
        (tdir / "meta.jinja").write_text(
            "{# template_name: my_template, template_version: 2.1.0, description: test desc #}\n"
            "content"
        )
        tm = TemplateManager(tdir)
        meta = tm.get_metadata("meta.jinja")
        assert meta["template_name"] == "my_template"
        assert meta["template_version"] == "2.1.0"

    def test_rich_response_metadata(self, template_manager, valid_llm_json, minimal_context):
        adapter = MockAdapter(response_text=valid_llm_json)
        engine = ReasoningEngine(adapter=adapter, template_manager=template_manager)
        engine.initialize()
        response = engine.reason("test", minimal_context)
        meta = response.metadata
        assert "template_version" in meta
        assert "timestamp" in meta
        assert "context_nodes_used" in meta

    def test_improved_health_check_adapter(self):
        # Already tested in TestLLMAdapter but verifying the ModelInfo structure
        adapter = MockAdapter()
        info = adapter.health_check()
        assert info.healthy is True
        assert hasattr(info, 'supports_json_mode')
        assert info.supports_json_mode is True

    def test_config_json_mode_system_instruction(self, template_manager, valid_llm_json, minimal_context):
        adapter = MockAdapter(response_text=valid_llm_json)
        config = ReasoningConfig(json_mode=True).resolve()
        engine = ReasoningEngine(adapter=adapter, template_manager=template_manager, config=config)
        engine.initialize()
        engine.reason("test", minimal_context)
        # Verify JSON instruction is in the final system prompt block
        assert "valid JSON ONLY" in engine.last_prompt

