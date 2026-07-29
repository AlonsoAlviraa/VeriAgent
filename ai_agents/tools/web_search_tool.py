"""
[TEAM-B][TOOL-003] WebSearchTool — zero-cost web research.

Herramienta de búsqueda web para el nodo `researcher` de ProductGraph.
Sigue la filosofía zero-cost del repositorio (ver LEER.md / llm_router.py):
sin API key, sin tarjeta de crédito.

Backend por defecto: DuckDuckGo (duckduckgo-search). La dependencia es
OPCIONAL: si no está instalada, el tool degrada a un mensaje claro en lugar
de romper el grafo o la colección de tests (mismo patrón que ChromaDB en
services/vector_db.py).

La interfaz `search()` está pensada para que un backend alternativo
(Tavily, SerpAPI, Brave) pueda enchufarse más adelante cambiando solo el
método `_backend`.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

try:
    from crewai_tools import BaseTool
except Exception:  # lightweight fallback when crewai not installed
    class BaseTool:  # type: ignore
        name: str = ""
        description: str = ""

        def _run(self, *a, **k):
            raise NotImplementedError

try:
    from pydantic import BaseModel, Field
except Exception:  # pragma: no cover - pydantic is a hard dep elsewhere
    BaseModel = object  # type: ignore

    def Field(*a, **k):  # type: ignore
        return None

# Optional backend — imported lazily/safely so absence never breaks imports.
try:
    from duckduckgo_search import DDGS  # type: ignore

    _HAS_DDG = True
except Exception:
    DDGS = None  # type: ignore
    _HAS_DDG = False


logger = logging.getLogger(__name__)


# ============================================================
# PUBLIC DATA MODEL
# ============================================================

class WebSearchInput(BaseModel):
    query: str = Field(..., description="The search query to research")
    max_results: int = Field(default=6, description="Max number of results to return")


@dataclass
class WebSearchResult:
    """Single normalized search hit, backend-agnostic."""
    title: str
    url: str
    snippet: str

    def to_dict(self) -> Dict[str, str]:
        return {"title": self.title, "url": self.url, "snippet": self.snippet}


# ============================================================
# CORE SEARCH FUNCTION (no CrewAI required — used by tests + agents)
# ============================================================

UNAVAILABLE_MESSAGE = (
    "WEB_SEARCH_UNAVAILABLE: duckduckgo-search is not installed. "
    "Install with `pip install duckduckgo-search` to enable web research. "
    "Proceeding with LLM parametric knowledge only."
)


def search(
    query: str, max_results: int = 6, *, backend: Optional[str] = None
) -> Dict[str, Any]:
    """
    Zero-cost web search entrypoint used by agents and unit tests.

    Returns a normalized dict:
        {
          "available": bool,
          "query": str,
          "results": [{"title","url","snippet"}, ...],
          "sources": [url, ...],
        }

    When the backend is unavailable (lib missing or runtime error), returns
    `available=False` with an empty result set and a diagnostic message — it
    NEVER raises, so the graph can degrade gracefully.
    """
    query = (query or "").strip()
    if not query:
        return {
            "available": _HAS_DDG,
            "query": "",
            "results": [],
            "sources": [],
            "message": "Empty query",
        }

    if not _HAS_DDG:
        logger.warning("[WebSearch] Backend no disponible (duckduckgo-search ausente).")
        return {
            "available": False,
            "query": query,
            "results": [],
            "sources": [],
            "message": UNAVAILABLE_MESSAGE,
        }

    results: List[WebSearchResult] = []
    try:
        # Soportar ambas APIs: DDGS como context manager (v<8) y DDGS directo
        # (v8+ / paquete renombrado `ddgs`).
        # duckduckgo_search v8 emite un RuntimeWarning de "renamed to ddgs" al
        # instanciarse que escapa a filterwarnings (se imprime a stderr desde
        # un import hook). Lo silenciamos redirigiendo stderr durante la
        # instanciación — es ruido de deprecation, no un error.
        import io
        import contextlib

        with contextlib.redirect_stderr(io.StringIO()):
            ddgs = DDGS()  # type: ignore[union-attr]
        _cm = hasattr(ddgs, "__enter__")
        if _cm:
            ddgs.__enter__()
        try:
            raw = ddgs.text(query, max_results=max_results)
            for hit in raw or []:
                # duckduckgo_search keys: title / href / body / source ...
                title = hit.get("title") or hit.get("source") or ""
                url = hit.get("href") or hit.get("url") or hit.get("link") or ""
                snippet = hit.get("body") or hit.get("snippet") or ""
                if not url:
                    continue
                results.append(WebSearchResult(title=title, url=url, snippet=snippet))
        finally:
            if _cm:
                ddgs.__exit__(None, None, None)
    except Exception as exc:  # network errors, rate limits, etc.
        logger.warning("[WebSearch] Error durante la búsqueda: %s", exc)
        return {
            "available": False,
            "query": query,
            "results": [],
            "sources": [],
            "message": f"WEB_SEARCH_ERROR: {exc}",
        }

    # DDG puede devolver vacío por rate-limit/anti-bot transitorio. Lo señalamos
    # para que el caller (researcher) sepa que el backend respondió pero sin hits.
    if not results:
        return {
            "available": True,
            "query": query,
            "results": [],
            "sources": [],
            "message": "WEB_SEARCH_EMPTY: backend responded but returned no hits (rate-limit/anti-bot).",
        }

    return {
        "available": True,
        "query": query,
        "results": [r.to_dict() for r in results],
        "sources": [r.url for r in results],
    }


# ============================================================
# CREWAI TOOL WRAPPER (drop-in for agents that want a BaseTool)
# ============================================================

class WebSearchTool(BaseTool):
    name: str = "web_search"
    description: str = (
        "Search the live web (zero-cost DuckDuckGo) for fresh market and "
        "technical evidence. Returns titles, URLs and snippets with citations."
    )
    args_schema: type = WebSearchInput

    def _run(self, query: str, max_results: int = 6) -> str:
        data = search(query, max_results=max_results)
        if not data.get("available"):
            return data.get("message", UNAVAILABLE_MESSAGE)

        chunks: List[str] = []
        for i, r in enumerate(data["results"], start=1):
            chunks.append(
                f"[{i}] {r['title']}\n    {r['url']}\n    {r['snippet']}"
            )
        if not chunks:
            return "No web results found."
        return "\n".join(chunks)
