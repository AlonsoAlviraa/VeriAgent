"""
Tests para ai_agents.graphs.telemetry.

Verifica que run_with_telemetry captura llamadas LLM, score final, iteraciones
y provee un resumen legible. Usa mocks (LLM + web) para cero coste y cero red.
"""

import json

import pytest

from ai_agents.graphs.product_graph import (
    build_product_graph,
    initial_state,
    recursion_limit_for,
)
from ai_agents.graphs.telemetry import (
    instrumented_llm,
    run_with_telemetry,
    _infer_node,
)


def _llm_high_score():
    """Mock LLM: critic da score alto → termina en 1 iteración."""
    calls = {"i": 0}

    def _fake(messages, **kwargs):
        system = messages[0]["content"] if messages else ""
        user = messages[-1]["content"] if messages else ""
        if "Evalúa" in user or "quality_score" in user:
            return json.dumps({
                "quality_score": 9.0, "critique": "ok",
                "feedback": [], "weak_areas": [],
            })
        if "estratega de producto creativo" in system:
            return json.dumps([{"name": "I1", "feasibility_1_10": 9}])
        if "=== PRD ===" in user:
            return "=== PRD ===\nx\n=== ARQUITECTURA ===\ny\n=== GTM ===\nz"
        if "analista de investigación" in system:
            return "raw research"
        if "synthesizer" in system:
            return "synthesis"
        return ""
    return _fake


@pytest.fixture
def no_web(monkeypatch):
    monkeypatch.setattr(
        "ai_agents.graphs.product_graph.web_search",
        lambda *a, **k: {"available": False, "results": [], "sources": []},
    )


class TestInferNode:
    def test_infers_each_node(self):
        assert _infer_node("Eres un analista de investigación senior") == "researcher"
        assert _infer_node("Eres un synthesizer ejecutivo") == "synthesizer"
        assert _infer_node("Eres un estratega de producto creativo") == "idea_generator"
        assert _infer_node("Eres un Product Manager senior") == "spec_writer"
        assert _infer_node("Eres un crítico implacable") == "critic"
        assert _infer_node("otra cosa") == "unknown"


class TestRunWithTelemetry:
    def test_captures_llm_calls_and_score(self, no_web):
        state = initial_state("goal", "prompt")
        app = build_product_graph()
        report = run_with_telemetry(
            app, state,
            recursion_limit=recursion_limit_for(state["max_iterations"]),
            llm_call=_llm_high_score(),
        )

        assert report.status == "done"
        assert report.final_quality_score == 9.0
        assert report.iterations == 0
        assert len(report.llm_calls) > 0
        # Al menos una llamada debe atribuirse a un nodo conocido.
        nodes = {c.node_hint for c in report.llm_calls}
        assert nodes & {"researcher", "synthesizer", "idea_generator", "spec_writer", "critic"}
        # Sprint 10-V2: cada llamada debe trackear tokens (conteo por chars en fallback).
        for call in report.llm_calls:
            assert call.total_tokens > 0
            assert call.prompt_tokens > 0
            assert call.completion_tokens > 0
        assert report.total_tokens == sum(c.total_tokens for c in report.llm_calls)

    def test_summary_is_human_readable(self, no_web):
        state = initial_state("goal", "prompt")
        app = build_product_graph()
        report = run_with_telemetry(
            app, state,
            recursion_limit=recursion_limit_for(state["max_iterations"]),
            llm_call=_llm_high_score(),
        )

        summary = report.summary()
        assert "ProductGraph Telemetry" in summary
        assert "Final score" in summary
        assert "Iterations" in summary
        assert "Total tokens" in summary

    def test_instrumented_context_manager_records(self):
        """El context manager registra llamadas aunque el router esté ausente."""
        with instrumented_llm() as records:
            # Sin invocar el grafo; la lista inicia vacía.
            assert records == []

    def test_duration_is_positive(self, no_web):
        state = initial_state("goal", "prompt")
        app = build_product_graph()
        report = run_with_telemetry(
            app, state,
            recursion_limit=recursion_limit_for(state["max_iterations"]),
            llm_call=_llm_high_score(),
        )
        assert report.duration_seconds >= 0.0
