"""
Tests para cost_guard (Sprint 5-V2) + API del ProductGraph.
"""

import json
import time
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from ai_agents.graphs.cost_guard import (
    DEFAULT_TOKEN_BUDGET,
    BudgetExceeded,
    BudgetTracker,
    budgeted_run,
)
from ai_agents.graphs.jobs import GraphJobStore


# ============================================================
# LLM mocks
# ============================================================

def _llm_high_score():
    """LLM mock: critic da score alto → termina en 1 iteración."""
    def _fake(messages, **kwargs):
        system = messages[0]["content"] if messages else ""
        user = messages[-1]["content"] if messages else ""
        if "Evalúa" in user or "quality_score" in user:
            return json.dumps({"quality_score": 9.0, "critique": "ok", "feedback": [], "weak_areas": []})
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


def _llm_cheap_filler():
    """LLM mock que devuelve texto corto (pocos tokens)."""
    def _fake(messages, **kwargs):
        system = messages[0]["content"] if messages else ""
        user = messages[-1]["content"] if messages else ""
        if "quality_score" in user or "Evalúa" in user:
            return json.dumps({"quality_score": 3.0, "critique": "", "feedback": ["x"], "weak_areas": ["research","ideas","spec"]})
        if "estratega" in system:
            return json.dumps([{"name": "I"}])
        if "=== PRD ===" in user:
            return "=== PRD ===\nx\n=== ARQUITECTURA ===\ny\n=== GTM ===\nz"
        if "analista" in system:
            return "r"
        if "synthesizer" in system:
            return "s"
        return ""
    return _fake


# ============================================================
# BUDGET TRACKER
# ============================================================

class TestBudgetTracker:
    def test_consume_under_budget(self):
        t = BudgetTracker(budget=1000)
        t.consume(300)
        t.consume(400)
        assert t.used == 700
        assert t.remaining == 300
        assert not t.aborted

    def test_consume_exceeds_raises(self):
        t = BudgetTracker(budget=100)
        t.consume(60)
        with pytest.raises(BudgetExceeded):
            t.consume(50)
        assert t.aborted

    def test_unlimited_budget(self):
        t = BudgetTracker(budget=0)
        t.consume(10_000_000)
        assert t.remaining == -1
        assert not t.aborted

    def test_to_dict(self):
        t = BudgetTracker(budget=100, used=30, call_count=2)
        d = t.to_dict()
        assert d["budget"] == 100 and d["used"] == 30 and d["call_count"] == 2


# ============================================================
# BUDGETED RUN
# ============================================================

class TestBudgetedRun:
    def test_run_completes_under_budget(self):
        with patch("ai_agents.graphs.product_graph._chat_completion", side_effect=_llm_high_score()):
            result = budgeted_run("g", "p", budget=500_000, llm_call=None, no_web=True)
        assert result["status"] in ("done", "failed")
        budget = result["_meta"]["budget"]
        assert budget["used"] > 0
        assert not budget["aborted"]

    def test_run_aborts_on_budget_exceeded(self):
        # Budget bajísimo → debe abortar con budget_exceeded.
        with patch("ai_agents.graphs.product_graph._chat_completion", side_effect=_llm_cheap_filler()):
            result = budgeted_run("g", "p", budget=50, max_iterations=6, llm_call=None, no_web=True)
        assert result["status"] == "budget_exceeded"
        budget = result["_meta"]["budget"]
        assert budget["aborted"] is True
        assert "Presupuesto Excedido" in result["final_report"]


# ============================================================
# JOB STORE
# ============================================================

class TestGraphJobStore:
    def test_submit_sync_completes(self):
        store = GraphJobStore()
        with patch("ai_agents.graphs.product_graph._chat_completion", side_effect=_llm_high_score()):
            job = store.submit("goal", "prompt", budget=500_000, max_iterations=2, background=False)
        assert job.status in ("done", "failed")
        assert job.result is not None
        assert job.finished_at

    def test_get_unknown_returns_none(self):
        store = GraphJobStore()
        assert store.get("nope") is None

    def test_list_returns_metadata(self):
        store = GraphJobStore()
        with patch("ai_agents.graphs.product_graph._chat_completion", side_effect=_llm_high_score()):
            store.submit("g1", "p", budget=500_000, max_iterations=2, background=False)
            store.submit("g2", "p", budget=500_000, max_iterations=2, background=False)
        listing = store.list()
        assert listing["count"] == 2
        assert all("id" in j and "status" in j for j in listing["jobs"])

    def test_clear(self):
        store = GraphJobStore()
        with patch("ai_agents.graphs.product_graph._chat_completion", side_effect=_llm_high_score()):
            store.submit("g", "p", budget=500_000, max_iterations=2, background=False)
        store.clear()
        assert store.list()["count"] == 0

    def test_async_background_eventually_completes(self):
        store = GraphJobStore()
        with patch("ai_agents.graphs.product_graph._chat_completion", side_effect=_llm_high_score()):
            job = store.submit("g", "p", budget=500_000, max_iterations=2, background=True)
            # Esperar a que termine (timeout 10s).
            for _ in range(100):
                if store.get(job.id).status not in ("pending", "running"):
                    break
                time.sleep(0.1)
        assert store.get(job.id).status in ("done", "failed")


# ============================================================
# API ENDPOINTS
# ============================================================

@pytest.fixture
def client():
    from core_engine.main import app
    return TestClient(app)


@pytest.fixture(autouse=True)
def _reset_job_store():
    """Aísla el job store singleton entre tests."""
    from ai_agents.graphs import jobs
    jobs._job_store = None
    yield
    jobs._job_store = None


class TestProductGraphAPI:
    def test_submit_run_returns_202(self, client):
        with patch("ai_agents.graphs.product_graph._chat_completion", side_effect=_llm_high_score()):
            r = client.post("/api/v1/product-graph/runs", json={"goal": "api-goal", "prompt": "p"})
        assert r.status_code == 202
        data = r.json()
        assert "job_id" in data
        assert data["status"] in ("pending", "running", "done")
        assert data["goal"] == "api-goal"

    def test_get_run_status(self, client):
        with patch("ai_agents.graphs.product_graph._chat_completion", side_effect=_llm_high_score()):
            submit = client.post("/api/v1/product-graph/runs", json={"goal": "g", "prompt": "p"})
            job_id = submit.json()["job_id"]
            # Esperar finalización.
            for _ in range(100):
                get = client.get(f"/api/v1/product-graph/runs/{job_id}")
                if get.json()["status"] not in ("pending", "running"):
                    break
                time.sleep(0.1)
        assert get.status_code == 200
        d = get.json()
        assert d["status"] in ("done", "failed")
        assert "final_report" in d
        assert "quality_score" in d

    def test_get_unknown_run_404(self, client):
        r = client.get("/api/v1/product-graph/runs/missing-id")
        assert r.status_code == 404

    def test_list_runs(self, client):
        with patch("ai_agents.graphs.product_graph._chat_completion", side_effect=_llm_high_score()):
            client.post("/api/v1/product-graph/runs", json={"goal": "g1", "prompt": "p"})
        r = client.get("/api/v1/product-graph/runs")
        assert r.status_code == 200
        assert r.json()["count"] >= 1

    def test_health_endpoint(self, client):
        r = client.get("/api/v1/product-graph/health")
        assert r.status_code == 200
        d = r.json()
        assert d["status"] == "ok"
        assert d["service"] == "product_graph"
        assert "recent_runs" in d

    def test_dashboard_endpoint(self, client):
        with patch("ai_agents.graphs.product_graph._chat_completion", side_effect=_llm_high_score()):
            client.post("/api/v1/product-graph/runs", json={"goal": "g", "prompt": "p"})
            # esperar a que termine
            for _ in range(100):
                listing = client.get("/api/v1/product-graph/runs").json()
                if listing["count"] and all(
                    j["status"] not in ("pending", "running") for j in listing["jobs"]
                ):
                    break
                time.sleep(0.1)
        r = client.get("/api/v1/product-graph/dashboard")
        assert r.status_code == 200
        d = r.json()
        assert d["total_runs"] >= 1
        assert "avg_quality_score" in d
        assert "total_tokens_used" in d
        assert d["estimated_cost_usd"] == 0.0

    def test_submit_validates_required_goal(self, client):
        r = client.post("/api/v1/product-graph/runs", json={"prompt": "p"})
        assert r.status_code == 422
