"""
Tests para deep_research y critic_rubric (Sprint 3-V2).
"""

import json
from unittest.mock import patch

import pytest

from ai_agents.graphs.deep_research import (
    DEFAULT_RESEARCH_CYCLES,
    MAX_RESEARCH_CYCLES,
    ResearchResult,
    deep_research,
    _dedupe,
    _derive_initial_queries,
    _safe_json_obj,
)
from ai_agents.graphs.critic_rubric import (
    AXIS_WEIGHTS,
    FeedbackMemory,
    RubricCritique,
    RubricScore,
    critique_with_rubric,
    _aggregate,
)


# ============================================================
# DEEP RESEARCH
# ============================================================

def _web_mock(queries_seen):
    """Web search mock que registra queries y devuelve hits."""
    def _search(query, max_results=4):
        queries_seen.append(query)
        return {
            "available": True,
            "results": [
                {"title": f"T-{query}", "url": f"http://x/{abs(hash(query))%100}",
                 "snippet": f"snippet about {query}"},
            ],
            "sources": [f"http://x/{query}"],
        }
    return _search


def _reflect_llm(gap_queries_by_cycle):
    """LLM mock: la reflexión devuelve gap_queries según el ciclo."""
    calls = {"i": 0}

    def _llm(system, user, **kw):
        if "reflexivo" in system or "gaps" in system.lower():
            cycle = calls["i"]
            calls["i"] += 1
            gqs = gap_queries_by_cycle[cycle] if cycle < len(gap_queries_by_cycle) else []
            return json.dumps({"gaps": ["gap1"] if gqs else [], "gap_queries": gqs})
        # Síntesis.
        return "## Mercado\nCrecimiento.\n## Competidores\nFoo."
    return _llm


class TestDeepResearch:
    def test_runs_search_reflect_cycles(self):
        queries = []
        web = _web_mock(queries)
        # Ciclo 0 propone nuevas queries, ciclo 1 no (termina).
        llm = _reflect_llm([["gap query A", "gap query B"], []])
        with patch("ai_agents.graphs.deep_research._llm_call", side_effect=llm):
            result = deep_research("goal", "prompt", max_cycles=2, search_fn=web)

        assert isinstance(result, ResearchResult)
        assert result.cycles_run >= 1
        # Las queries iniciales + las del gap deben haberse buscado.
        assert "gap query A" in result.queries_used
        assert "goal" in result.queries_used
        assert len(result.sources) > 0
        assert "Mercado" in result.raw_text

    def test_stops_when_no_gaps(self):
        queries = []
        web = _web_mock(queries)
        llm = _reflect_llm([[]])  # sin gaps en el primer ciclo
        with patch("ai_agents.graphs.deep_research._llm_call", side_effect=llm):
            result = deep_research("g", "p", max_cycles=3, search_fn=web)
        assert result.cycles_run == 1

    def test_caps_at_max_cycles(self):
        web = _web_mock([])
        llm = _reflect_llm([["q"], ["q"], ["q"], ["q"], ["q"]])  # siempre gaps
        with patch("ai_agents.graphs.deep_research._llm_call", side_effect=llm):
            result = deep_research("g", "p", max_cycles=99, search_fn=web)
        assert result.cycles_run == MAX_RESEARCH_CYCLES

    def test_web_unavailable_degrades_gracefully(self):
        web = lambda q, max_results=4: {"available": False, "results": [], "sources": []}
        llm = _reflect_llm([[]])
        with patch("ai_agents.graphs.deep_research._llm_call", side_effect=llm):
            result = deep_research("g", "p", search_fn=web)
        assert result.cycles_run >= 1
        # Sin fuentes pero sí síntesis.
        assert result.sources == []
        assert "Mercado" in result.raw_text

    def test_derive_initial_queries(self):
        qs = _derive_initial_queries("mi goal", "frase corta\nfrase mucho mas larga que entra aqui ok")
        assert "mi goal" in qs
        assert len(qs) <= 3

    def test_dedupe_preserves_order(self):
        assert _dedupe(["a", "b", "a", "c", "b"]) == ["a", "b", "c"]

    def test_retry_on_web_search_empty(self, monkeypatch):
        """WEB_SEARCH_EMPTY dispara reintento; si luego hay hits, se usan."""
        from ai_agents.graphs import deep_research as dr
        calls = {"n": 0}

        def flaky_search(query, max_results=4):
            calls["n"] += 1
            if calls["n"] == 1:
                # Primera llamada: empty (anti-bot).
                return {"available": True, "results": [], "sources": [],
                        "message": "WEB_SEARCH_EMPTY: rate-limit"}
            # Reintento: hits reales.
            return {"available": True,
                    "results": [{"title": "X", "url": "http://y/1", "snippet": "s"}],
                    "sources": ["http://y/1"]}

        # Evitar sleep real en el backoff.
        monkeypatch.setattr(dr.time, "sleep", lambda *_: None)
        web = flaky_search
        llm = _reflect_llm([[]])
        with patch("ai_agents.graphs.deep_research._llm_call", side_effect=llm):
            result = dr.deep_research("g", "p", max_cycles=1, search_fn=web)
        # Debe haber reintentado y capturado el hit del segundo intento.
        assert calls["n"] >= 2
        assert "http://y/1" in result.sources

    def test_empty_search_recorded_as_no_hits(self, monkeypatch):
        """Si la búsqueda siempre devuelve empty, se registra como sin hits."""
        from ai_agents.graphs import deep_research as dr
        monkeypatch.setattr(dr.time, "sleep", lambda *_: None)
        web = lambda q, max_results=4: {"available": True, "results": [], "sources": [],
                                        "message": "WEB_SEARCH_EMPTY"}
        llm = _reflect_llm([[]])
        with patch("ai_agents.graphs.deep_research._llm_call", side_effect=llm):
            result = dr.deep_research("g", "p", max_cycles=1, search_fn=web)
        assert result.sources == []
        # La síntesis aún se produce (con evidencia vacía).
        assert "Mercado" in result.raw_text


# ============================================================
# CRITIC RUBRIC
# ============================================================

def _rubric_llm(axes_scores):
    """LLM mock que devuelve scores por eje."""
    def _llm(system, user, **kw):
        return json.dumps({
            "axes": [
                {"axis": ax, "score": sc, "justification": f"j-{ax}"}
                for ax, sc in axes_scores.items()
            ],
            "critique": "Global ok",
            "feedback": ["mejorar X", "revisar Y"],
            "weak_areas": ["spec"],
        })
    return _llm


class TestCriticRubric:
    def test_returns_four_axes(self):
        state = {"goal": "g", "product_spec": "PRD", "technical_architecture": "A",
                 "gtm_strategy": "G", "research_synthesis": "S", "product_ideas": [{"name": "I"}]}
        with patch("ai_agents.graphs.critic_rubric._llm_call",
                   side_effect=_rubric_llm({"completitud": 9, "realismo": 8, "originalidad": 7, "acionabilidad": 9})):
            critique = critique_with_rubric(state)
        axis_names = {a.axis for a in critique.axes}
        assert axis_names == {"completitud", "realismo", "originalidad", "acionabilidad"}
        assert critique.global_score > 0
        assert critique.feedback == ["mejorar X", "revisar Y"]
        assert critique.weak_areas == ["spec"]

    def test_missing_axis_filled_with_zero(self):
        state = {"goal": "g"}
        # El LLM solo devuelve 2 ejes; los otros se rellenan con 0.
        with patch("ai_agents.graphs.critic_rubric._llm_call",
                   side_effect=_rubric_llm({"completitud": 9, "realismo": 8})):
            critique = critique_with_rubric(state)
        by_axis = {a.axis: a.score for a in critique.axes}
        assert by_axis["originalidad"] == 0.0
        assert by_axis["completitud"] == 9.0

    def test_aggregate_uses_weights(self):
        axes = [
            RubricScore("completitud", 10), RubricScore("realismo", 10),
            RubricScore("originalidad", 10), RubricScore("acionabilidad", 10),
        ]
        assert _aggregate(axes) == 10.0
        # Si todos son 0, global es 0.
        axes0 = [RubricScore(a, 0) for a in AXIS_WEIGHTS]
        assert _aggregate(axes0) == 0.0

    def test_global_score_bounded_0_10(self):
        axes = [RubricScore(a, 10) for a in AXIS_WEIGHTS]
        # Suma de pesos = 1.0 → max 10.0
        assert _aggregate(axes) == 10.0

    def test_handles_malformed_llm_json(self):
        state = {"goal": "g"}
        with patch("ai_agents.graphs.critic_rubric._llm_call", return_value="not json"):
            critique = critique_with_rubric(state)
        # Debe devolver 4 ejes en 0 sin romper.
        assert len(critique.axes) == 4
        assert critique.global_score == 0.0


class TestFeedbackMemory:
    def test_record_and_load(self, tmp_path):
        mem = FeedbackMemory(path=str(tmp_path / "fb.json"))
        critique = RubricCritique(
            axes=[], global_score=8.0,
            feedback=["gap A", "gap B"],
        )
        mem.record(critique, thread_id="t1")
        loaded = mem.load()
        assert "gap A" in loaded
        assert "gap B" in loaded

    def test_recurring_returns_top(self, tmp_path):
        mem = FeedbackMemory(path=str(tmp_path / "fb.json"))
        for _ in range(3):
            mem.record(RubricCritique(global_score=5.0, feedback=["mismo error"]), thread_id="t")
        rec = mem.recurring(top_n=1)
        assert any("mismo error" in r for r in rec)

    def test_load_nonexistent_returns_empty(self, tmp_path):
        mem = FeedbackMemory(path=str(tmp_path / "nope.json"))
        assert mem.load() == []

    def test_clear(self, tmp_path):
        mem = FeedbackMemory(path=str(tmp_path / "fb.json"))
        mem.record(RubricCritique(global_score=5.0, feedback=["x"]))
        assert mem.load()
        mem.clear()
        assert mem.load() == []

    def test_capped_at_100(self, tmp_path):
        mem = FeedbackMemory(path=str(tmp_path / "fb.json"))
        for i in range(150):
            mem.record(RubricCritique(global_score=5.0, feedback=[f"fb-{i}"]))
        # La memoria interna guarda hasta 100 items, pero load devuelve feedbacks.
        # Verificamos que no crece sin límite leyendo el JSON crudo.
        import json
        with open(mem.path) as f:
            data = json.load(f)
        assert len(data["items"]) == 100
