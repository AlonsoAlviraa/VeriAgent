"""
Tests for ai_agents.tools.web_search_tool.

No se toca la red: se mockea el backend duckduckgo_search y se simula
también la ausencia de la librería para verificar la degradación elegante.
"""

import sys
import types
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Fixtures de módulo: garantizan que el backend parezca INSTALADO para la
# mayoría de tests, aunque duckduckgo-search no lo esté en el entorno.
# ---------------------------------------------------------------------------

def _make_fake_ddgs_module(hits_per_query=3):
    """Crea un módulo duckduckgo_search falso con DDGS devolviendo hits."""

    class _FakeDDGS:
        def __init__(self, *a, **k):
            self.calls = 0

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def text(self, query, max_results=5):
            self.calls += 1
            return [
                {
                    "title": f"Resultado {i} para {query}",
                    "href": f"https://example.com/{i}/{abs(hash(query)) % 1000}",
                    "body": f"Snippet {i} sobre {query}",
                }
                for i in range(min(hits_per_query, max_results))
            ]

    mod = types.ModuleType("duckduckgo_search")
    mod.DDGS = _FakeDDGS
    return mod


@pytest.fixture
def fake_ddgs(monkeypatch):
    mod = _make_fake_ddgs_module()
    monkeypatch.setitem(sys.modules, "duckduckgo_search", mod)
    # Recargar el módulo del tool para que tome la lib falsa.
    import importlib
    import ai_agents.tools.web_search_tool as wst
    importlib.reload(wst)
    yield wst
    importlib.reload(wst)  # restaurar al estado real al final


@pytest.fixture
def no_ddgs(monkeypatch):
    """Simula que duckduckgo_search NO está instalado."""
    monkeypatch.setitem(sys.modules, "duckduckgo_search", None)
    import importlib
    import ai_agents.tools.web_search_tool as wst
    importlib.reload(wst)
    yield wst
    importlib.reload(wst)


# ---------------------------------------------------------------------------
# Tests: backend disponible
# ---------------------------------------------------------------------------

class TestWebSearchAvailable:
    def test_returns_normalized_structure(self, fake_ddgs):
        data = fake_ddgs.search("mercado SaaS", max_results=3)
        assert data["available"] is True
        assert data["query"] == "mercado SaaS"
        assert isinstance(data["results"], list)
        assert len(data["results"]) == 3
        assert len(data["sources"]) == 3
        r = data["results"][0]
        assert {"title", "url", "snippet"} <= set(r.keys())

    def test_sources_match_result_urls(self, fake_ddgs):
        data = fake_ddgs.search("IA generativa", max_results=2)
        assert data["sources"] == [r["url"] for r in data["results"]]

    def test_max_results_limits_hits(self, fake_ddgs):
        data = fake_ddgs.search("x", max_results=1)
        assert len(data["results"]) == 1

    def test_empty_query_returns_empty(self, fake_ddgs):
        data = fake_ddgs.search("   ")
        assert data["results"] == []
        assert data["sources"] == []

    def test_skips_hits_without_url(self, monkeypatch):
        mod = _make_fake_ddgs_module()
        # Parchar text() para que un hit venga sin href.
        original_text = mod.DDGS.text

        def patched(self, query, max_results=5):
            hits = original_text(self, query, max_results)
            hits[0]["href"] = ""  # sin URL → debe descartarse
            return hits

        mod.DDGS.text = patched
        monkeypatch.setitem(sys.modules, "duckduckgo_search", mod)
        import importlib
        import ai_agents.tools.web_search_tool as wst
        importlib.reload(wst)
        try:
            data = wst.search("q", max_results=2)
            assert all(r["url"] for r in data["results"])
        finally:
            importlib.reload(wst)

    def test_tool_run_formats_citations(self, fake_ddgs):
        tool = fake_ddgs.WebSearchTool()
        out = tool._run("mercado fintech", max_results=2)
        assert isinstance(out, str)
        assert "http" in out
        assert "[1]" in out


# ---------------------------------------------------------------------------
# Tests: backend NO disponible (degradación elegante)
# ---------------------------------------------------------------------------

class TestWebSearchUnavailable:
    def test_unavailable_flag_when_lib_missing(self, no_ddgs):
        data = no_ddgs.search("cualquier cosa")
        assert data["available"] is False
        assert data["results"] == []
        assert "WEB_SEARCH_UNAVAILABLE" in data["message"]

    def test_search_never_raises_on_runtime_error(self, monkeypatch):
        # Backend presente pero lanza excepción en tiempo de ejecución.
        mod = _make_fake_ddgs_module()

        class _BoomDDGS(mod.DDGS):
            def text(self, *a, **k):
                raise RuntimeError("network down")

        mod.DDGS = _BoomDDGS
        monkeypatch.setitem(sys.modules, "duckduckgo_search", mod)
        import importlib
        import ai_agents.tools.web_search_tool as wst
        importlib.reload(wst)
        try:
            data = wst.search("q")
            assert data["available"] is False
            assert "WEB_SEARCH_ERROR" in data["message"]
        finally:
            importlib.reload(wst)
