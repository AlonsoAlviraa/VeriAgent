"""
Tests para ai_agents.graphs.runtime + cli (Sprint 1-V2).

Verifica:
- run_persistent persiste artifacts (state.json + report.md) a disco.
- save_run_artifacts / load_run_state / list_runs redondos.
- run_streaming emite eventos por nodo.
- CLI: run / list / show (salida y exit codes).
"""

import json
import os
from unittest.mock import patch

import pytest

from ai_agents.graphs import runtime
from ai_agents.graphs.runtime import (
    RUNS_DIR,
    list_runs,
    load_run_state,
    new_thread_id,
    run_persistent,
    run_streaming,
    save_run_artifacts,
)


# LLM mock de alta calidad (termina en 1 iteración).
def _llm_high_score():
    import json as _json

    def _fake(messages, **kwargs):
        system = messages[0]["content"] if messages else ""
        user = messages[-1]["content"] if messages else ""
        if "Evalúa" in user or "quality_score" in user:
            return _json.dumps({
                "quality_score": 9.0, "critique": "ok",
                "feedback": [], "weak_areas": [],
            })
        if "estratega de producto creativo" in system:
            return _json.dumps([{"name": "I1", "feasibility_1_10": 9}])
        if "=== PRD ===" in user:
            return "=== PRD ===\nx\n=== ARQUITECTURA ===\ny\n=== GTM ===\nz"
        if "analista de investigación" in system:
            return "raw research"
        if "synthesizer" in system:
            return "synthesis"
        return ""
    return _fake


@pytest.fixture
def isolated_runs_dir(tmp_path, monkeypatch):
    """Aísla el directorio de runs por test."""
    monkeypatch.setattr(runtime, "RUNS_DIR", str(tmp_path / "runs"))
    return runtime.RUNS_DIR


@pytest.fixture
def no_web(monkeypatch):
    monkeypatch.setattr(
        "ai_agents.graphs.product_graph.web_search",
        lambda *a, **k: {"available": False, "results": [], "sources": []},
    )


class TestPersistence:
    def test_save_and_load_run_state(self, isolated_runs_dir):
        state = {
            "goal": "g", "mega_prompt": "p", "status": "done",
            "quality_score": 8.5, "iteration": 0, "max_iterations": 6,
            "final_report": "# Report\ncontenido",
        }
        d = save_run_artifacts("tid-1", state)
        assert os.path.isdir(d)
        assert os.path.exists(os.path.join(d, "state.json"))
        assert os.path.exists(os.path.join(d, "report.md"))

        loaded = load_run_state("tid-1")
        assert loaded is not None
        assert loaded["status"] == "done"
        assert loaded["quality_score"] == 8.5
        # messages no se persiste.
        assert "messages" not in loaded

    def test_load_nonexistent_returns_none(self, isolated_runs_dir):
        assert load_run_state("nope") is None

    def test_list_runs(self, isolated_runs_dir):
        save_run_artifacts("a", {"goal": "ga", "status": "done", "quality_score": 9.0, "iteration": 0})
        save_run_artifacts("b", {"goal": "gb", "status": "failed", "quality_score": 3.0, "iteration": 6})
        runs = list_runs()
        ids = {r["thread_id"] for r in runs}
        assert ids == {"a", "b"}
        by_id = {r["thread_id"]: r for r in runs}
        assert by_id["a"]["quality_score"] == 9.0

    def test_list_runs_empty(self, isolated_runs_dir):
        assert list_runs() == []

    def test_new_thread_id_is_unique(self):
        a = new_thread_id()
        b = new_thread_id()
        assert a != b
        assert len(a) > 10


class TestRunPersistent:
    def test_run_persists_artifacts(self, isolated_runs_dir, no_web):
        with patch("ai_agents.graphs.product_graph._chat_completion", side_effect=_llm_high_score()):
            result = run_persistent("goal-x", "prompt-y", save_artifacts=True)

        assert result["status"] == "done"
        meta = result["_meta"]
        tid = meta["thread_id"]
        assert meta["artifacts_dir"] is not None
        # Los artifacts existen en disco.
        state = load_run_state(tid)
        assert state is not None
        assert state["goal"] == "goal-x"
        assert state["status"] == "done"

    def test_run_without_artifacts(self, isolated_runs_dir, no_web):
        with patch("ai_agents.graphs.product_graph._chat_completion", side_effect=_llm_high_score()):
            result = run_persistent("g", "p", save_artifacts=False)
        assert result["_meta"]["artifacts_dir"] is None
        assert load_run_state(result["_meta"]["thread_id"]) is None

    def test_run_with_explicit_thread_id(self, isolated_runs_dir, no_web):
        with patch("ai_agents.graphs.product_graph._chat_completion", side_effect=_llm_high_score()):
            result = run_persistent("g", "p", thread_id="fixed-id-123")
        assert result["_meta"]["thread_id"] == "fixed-id-123"


class TestStreaming:
    def test_stream_emits_events_per_node(self, isolated_runs_dir, no_web):
        events = list(run_streaming("g", "p"))
        # Al menos los nodos del grafo + END.
        nodes = [e.node for e in events]
        assert "END" in nodes
        # El primer evento tiene un nodo real del grafo.
        assert events[0].node in {"planner", "researcher", "synthesizer",
                                  "idea_generator", "spec_writer", "critic"}
        # Cada evento tiene timestamp y snapshot.
        for e in events:
            assert e.timestamp
            assert "status" in e.state_snapshot
            assert "iteration" in e.state_snapshot

    def test_stream_final_event_has_status(self, isolated_runs_dir, no_web):
        events = list(run_streaming("g", "p"))
        final = events[-1]
        assert final.node == "END"
        assert final.state_snapshot["status"] in {"done", "failed"}


class TestCLI:
    def test_cli_run_writes_artifacts(self, isolated_runs_dir, no_web, capsys):
        from ai_agents.graphs.cli import main
        with patch("ai_agents.graphs.product_graph._chat_completion", side_effect=_llm_high_score()):
            rc = main(["run", "--goal", "cli-goal", "--prompt", "p"])
        assert rc == 0
        # La run quedó persistida.
        runs = list_runs()
        assert any(r["goal"] == "cli-goal" for r in runs)

    def test_cli_list(self, isolated_runs_dir, capsys):
        from ai_agents.graphs.cli import main
        save_run_artifacts("cli-1", {"goal": "g1", "status": "done", "quality_score": 7.0, "iteration": 1})
        rc = main(["list"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "cli-1" in out
        assert "g1" in out

    def test_cli_list_json(self, isolated_runs_dir, capsys):
        from ai_agents.graphs.cli import main
        save_run_artifacts("cli-json", {"goal": "gj", "status": "done", "quality_score": 8.0, "iteration": 0})
        rc = main(["list", "--json"])
        assert rc == 0
        data = json.loads(capsys.readouterr().out)
        assert any(r["thread_id"] == "cli-json" for r in data)

    def test_cli_show_existing(self, isolated_runs_dir, capsys):
        from ai_agents.graphs.cli import main
        save_run_artifacts("show-1", {
            "goal": "g", "status": "done", "quality_score": 9.0,
            "iteration": 0, "final_report": "# My Report\nbody",
        })
        rc = main(["show", "--thread-id", "show-1"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "My Report" in out

    def test_cli_show_missing_returns_1(self, isolated_runs_dir):
        from ai_agents.graphs.cli import main
        rc = main(["show", "--thread-id", "missing"])
        assert rc == 1

    def test_cli_no_command_errors(self):
        from ai_agents.graphs.cli import main
        with pytest.raises(SystemExit):
            main([])
