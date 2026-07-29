"""
Tests for ai_agents.graphs.product_graph (ProductGraph).

El router LLM y la web search se mockean por completo: cero coste, cero red.
Se cubre:
- Finalización rápida cuando el critic da score alto (1 iteración).
- Loop de mejora cuando el critic da score bajo y sube en iteración 2.
- Contador duro (max_iterations) sin bucle infinito.
- Re-ejecución selectiva: el planner respeta weak_areas del improver.
- Selección determinista de la mejor idea y parseo robusto de JSON.
"""

import json
from unittest.mock import patch

import pytest

from ai_agents.graphs.product_graph import (
    DEFAULT_MAX_ITERATIONS,
    QUALITY_THRESHOLD,
    build_product_graph,
    initial_state,
    recursion_limit_for,
    _safe_parse_json_list,
    _safe_parse_json_obj,
    _select_best_idea,
    _split_spec_sections,
)


# ============================================================
# Helpers: mock LLM + web search
# ============================================================

def _critic_json(score, weak=None, feedback=None):
    return json.dumps({
        "quality_score": score,
        "critique": f"Score {score}",
        "feedback": feedback or ["mejorar X"],
        "weak_areas": weak or [],
    })


def _make_llm_mock(critic_score_sequence, weak_sequence=None, n_ideas=15):
    """
    Devuelve un side_effect para chat_completion que devuelve respuestas
    coherentes por nodo, controlando el score del critic según la secuencia.

    critic_score_sequence: lista de scores que el critic devolverá, uno por
    invocación del critic (el grafo pedirá uno por iteración).
    """
    critic_calls = {"i": 0}
    weak_sequence = weak_sequence or []

    def fake_chat(messages, temperature=0.7, max_tokens=4096, **kwargs):
        user = messages[-1]["content"] if messages else ""

        # --- researcher ---
        if "EVIDENCIA WEB" in user or "INVESTIGACIÓN" in user.upper() and "OBJETIVO" in user:
            return "## Mercado\nCrecimiento del 20% YoY.\n## Competidores\nFoo, Bar."

        # --- synthesizer ---
        if "Resume y prioriza" in user:
            return "### Insights top\n- Tendencia alza\n### Oportunidades\n- Nicho X"

        # --- idea_generator ---
        if "Genera entre" in user or "ideas de producto" in user:
            return json.dumps([
                {"name": f"Idea {i}", "one_liner": f"line {i}",
                 "feasibility_1_10": (10 - i)}
                for i in range(n_ideas)
            ])

        # --- spec_writer ---
        if "=== PRD ===" in user:
            return "=== PRD ===\nPRD body\n=== ARQUITECTURA ===\nArch body\n=== GTM ===\nGTM body"

        # --- critic ---
        if "quality_score" in user or "Evalúa" in user:
            idx = critic_calls["i"]
            critic_calls["i"] += 1
            score = (critic_score_sequence + [0.0])[idx] if idx < len(critic_score_sequence) else 0.0
            weak = (weak_sequence + [[]])[idx] if idx < len(weak_sequence) else []
            return _critic_json(score, weak)

        return ""

    return fake_chat


@pytest.fixture
def no_web(monkeypatch):
    """Evita cualquier llamada a red: web_search devuelve unavailable."""
    monkeypatch.setattr(
        "ai_agents.graphs.product_graph.web_search",
        lambda *a, **k: {"available": False, "results": [], "sources": [], "query": ""},
    )


# ============================================================
# UNIT: utilidades de parsing/selección
# ============================================================

class TestUtilities:
    def test_parse_json_list_direct(self):
        raw = '[{"a":1},{"a":2}]'
        assert len(_safe_parse_json_list(raw)) == 2

    def test_parse_json_list_embedded(self):
        raw = 'Aquí van: [{"a":1}] fin.'
        assert len(_safe_parse_json_list(raw)) == 1

    def test_parse_json_list_empty(self):
        assert _safe_parse_json_list("") == []
        assert _safe_parse_json_list("no json") == []

    def test_parse_json_obj_embedded(self):
        raw = 'texto {"quality_score": 9.1, "weak_areas": ["spec"]} texto'
        obj = _safe_parse_json_obj(raw)
        assert obj["quality_score"] == 9.1
        assert obj["weak_areas"] == ["spec"]

    def test_select_best_idea_highest_feasibility(self):
        ideas = [
            {"name": "A", "feasibility_1_10": 5},
            {"name": "B", "feasibility_1_10": 9},
            {"name": "C", "feasibility_1_10": 7},
        ]
        assert _select_best_idea(ideas)["name"] == "B"

    def test_select_best_idea_empty(self):
        assert _select_best_idea([])["name"]  # default name present

    def test_split_spec_sections(self):
        raw = "=== PRD ===\np1\n=== ARQUITECTURA ===\na1\n=== GTM ===\ng1"
        prd, arch, gtm = _split_spec_sections(raw)
        assert "p1" in prd and "a1" in arch and "g1" in gtm

    def test_split_spec_sections_fallback(self):
        prd, arch, gtm = _split_spec_sections("todo junto sin marcadores")
        assert prd == "todo junto sin marcadores"
        assert arch == "" and gtm == ""


# ============================================================
# INTEGRATION: comportamiento del grafo completo
# ============================================================

class TestProductGraphFlow:
    def test_high_score_finalizes_in_one_iteration(self, no_web):
        """Critic da score ≥ umbral → finalizer en la primera pasada."""
        fake = _make_llm_mock(critic_score_sequence=[9.5])
        state = initial_state("goal", "prompt")
        with patch("ai_agents.graphs.product_graph._chat_completion", side_effect=fake):
            app = build_product_graph()
            result = app.invoke(
                state, config={"recursion_limit": recursion_limit_for(state["max_iterations"])}
            )

        assert result["status"] == "done"
        assert result["quality_score"] >= QUALITY_THRESHOLD
        assert result["iteration"] == 0  # no hubo loop de mejora
        assert "Reporte Final" in result["final_report"]
        assert "PRD" in result["final_report"]

    def test_low_then_high_score_loops_once(self, no_web):
        """
        Critic da score bajo en iter 0, alto en iter 1.
        Debe pasar por improver → planner (loop) y terminar done.
        """
        fake = _make_llm_mock(critic_score_sequence=[5.0, 9.0])
        state = initial_state("goal", "prompt")
        with patch("ai_agents.graphs.product_graph._chat_completion", side_effect=fake):
            app = build_product_graph()
            result = app.invoke(
                state, config={"recursion_limit": recursion_limit_for(state["max_iterations"])}
            )

        assert result["status"] == "done"
        assert result["quality_score"] == 9.0
        assert result["iteration"] == 1  # el improver incrementó a 1

    def test_max_iterations_stops_without_infinite_loop(self, no_web):
        """Score siempre bajo → termina por max_iterations sin colgar."""
        fake = _make_llm_mock(critic_score_sequence=[3.0, 3.0, 3.0])
        state = initial_state("g", "p", max_iterations=2)
        with patch("ai_agents.graphs.product_graph._chat_completion", side_effect=fake):
            app = build_product_graph()
            result = app.invoke(
                state, config={"recursion_limit": recursion_limit_for(state["max_iterations"])}
            )

        # Alcanzó el máximo de iteraciones y empaquetó (no bucle infinito).
        assert result["iteration"] == 2
        assert result["status"] in ("done", "failed")
        assert result["quality_score"] < QUALITY_THRESHOLD
        assert "Reporte Final" in result["final_report"]

    def test_default_max_iterations_six(self):
        st = initial_state("g", "p")
        assert st["max_iterations"] == DEFAULT_MAX_ITERATIONS == 6

    def test_recursion_limit_covers_full_loop(self):
        # El límite debe cubrir (max_iter+1) pasadas de 7 pasos cada una + margen.
        from ai_agents.graphs.product_graph import _STEPS_PER_ITERATION
        for mx in (1, 2, 6, 10):
            rl = recursion_limit_for(mx)
            assert rl >= (mx + 1) * _STEPS_PER_ITERATION
        # Mínimo de 25 para no romper pasadas cortas.
        assert recursion_limit_for(1) >= 25


# ============================================================
# UNIT: planner re-ejecución selectiva
# ============================================================

class TestPlannerSelectiveReexecution:
    def test_planner_keeps_weak_areas_for_rerun(self):
        from ai_agents.graphs.product_graph import planner_node
        state = initial_state("g", "p")
        state["iteration"] = 1
        state["weak_areas"] = ["ideas", "spec"]

        out = planner_node(state)
        assert out["weak_areas"] == ["ideas", "spec"]
        # Como no hay 'research' en weak_areas, el status salta a generating.
        assert out["status"] == "generating"

    def test_planner_first_run_starts_researching(self):
        from ai_agents.graphs.product_graph import planner_node
        state = initial_state("g", "p")
        out = planner_node(state)
        assert out["status"] == "researching"
        assert out["weak_areas"] == []

    def test_improver_increments_iteration_and_keeps_weak(self):
        from ai_agents.graphs.product_graph import improver_node
        state = initial_state("g", "p")
        state["iteration"] = 1
        state["quality_score"] = 4.0
        state["weak_areas"] = ["research"]

        out = improver_node(state)
        assert out["iteration"] == 2
        assert out["status"] == "improving"
        assert out["weak_areas"] == ["research"]

    def test_improver_defaults_weak_when_critic_gave_none(self):
        from ai_agents.graphs.product_graph import improver_node
        state = initial_state("g", "p")
        state["iteration"] = 0
        state["weak_areas"] = []
        out = improver_node(state)
        assert set(out["weak_areas"]) == {"research", "ideas", "spec"}


# ============================================================
# UNIT: finalizer / routing
# ============================================================

class TestRoutingAndFinalizer:
    def test_route_high_score_finalizes(self):
        from ai_agents.graphs.product_graph import route_after_critic
        state = initial_state("g", "p")
        state["quality_score"] = 9.0
        assert route_after_critic(state) == "finalize"

    def test_route_low_score_under_max_improves(self):
        from ai_agents.graphs.product_graph import route_after_critic
        state = initial_state("g", "p")
        state["quality_score"] = 5.0
        state["iteration"] = 1
        state["max_iterations"] = 6
        assert route_after_critic(state) == "improve"

    def test_route_low_score_at_max_finalizes(self):
        from ai_agents.graphs.product_graph import route_after_critic
        state = initial_state("g", "p")
        state["quality_score"] = 5.0
        state["iteration"] = 6
        state["max_iterations"] = 6
        assert route_after_critic(state) == "finalize"

    def test_finalizer_report_contains_all_sections(self):
        from ai_agents.graphs.product_graph import finalizer_node
        state = initial_state("g", "p")
        state["selected_core_product"] = {"name": "Prod", "one_liner": "ola"}
        state["product_spec"] = "PRD body"
        state["technical_architecture"] = "Arch body"
        state["gtm_strategy"] = "GTM body"
        state["critique"] = "Buena"
        state["feedback"] = ["item 1"]
        state["sources"] = ["https://a.com"]

        out = finalizer_node(state)
        report = out["final_report"]
        for needle in ["Prod", "PRD body", "Arch body", "GTM body", "Buena", "item 1", "https://a.com"]:
            assert needle in report
        assert out["status"] in ("done", "failed")


class TestResearcherWebOnlyFallback:
    """Gap 2 (V2-iter): cuando el LLM degrada, el researcher construye un
    reporte mínimo con las fuentes web en vez de devolver vacío."""

    def test_web_only_research_with_sources(self):
        from ai_agents.graphs.product_graph import _web_only_research
        out = _web_only_research(
            "goal-x", "prompt-y",
            web_context="- [Titulo](http://a.com): snippet\n",
            sources=["http://a.com", "http://b.com"],
        )
        assert "modo web-only" in out
        assert "goal-x" in out
        assert "Titulo" in out
        assert "http://a.com" in out and "http://b.com" in out
        assert "Fuentes" in out

    def test_web_only_research_without_sources(self):
        from ai_agents.graphs.product_graph import _web_only_research
        out = _web_only_research("g", "p", web_context="(Sin resultados web)", sources=[])
        assert "No se recuperó evidencia web" in out

    def test_researcher_node_falls_back_when_llm_empty(self, monkeypatch):
        """Si _llm devuelve '' (router no disponible), research_raw no es vacío."""
        from ai_agents.graphs import product_graph as pg

        # LLM degradado: devuelve siempre vacío.
        monkeypatch.setattr(pg, "_chat_completion", None)
        # Web search mock con hits reales.
        monkeypatch.setattr(
            pg, "web_search",
            lambda q, max_results=5: {
                "available": True,
                "results": [{"title": "T1", "url": "http://hit/1", "snippet": "s1"}],
                "sources": ["http://hit/1"],
            },
        )
        state = {"goal": "g", "mega_prompt": "p"}
        out = pg.researcher_node(state)
        # research_raw no debe ser vacío: el fallback web-only lo construye.
        assert out["research_raw"]
        assert "http://hit/1" in out["research_raw"]
        assert "http://hit/1" in out["sources"]
        assert out["status"] == "generating"

    def test_researcher_node_uses_llm_when_available(self, monkeypatch):
        """Si _llm devuelve contenido, se usa la síntesis LLM (no el fallback)."""
        from ai_agents.graphs import product_graph as pg

        def fake_llm(system, user, **kw):
            return "## Mercado\nSíntesis LLM real."

        monkeypatch.setattr(pg, "_llm", fake_llm)
        monkeypatch.setattr(
            pg, "web_search",
            lambda q, max_results=5: {"available": True, "results": [], "sources": []},
        )
        state = {"goal": "g", "mega_prompt": "p"}
        out = pg.researcher_node(state)
        assert "Síntesis LLM real" in out["research_raw"]
        assert "web-only" not in out["research_raw"]
