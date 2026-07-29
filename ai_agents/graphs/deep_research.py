"""
[AGENT-017 / Sprint 3-V2] Deep researcher: multi-step research → reflect → search.

Mejora el nodo `researcher` del grafo con un bucle de investigación reflexiva:

    1. search(initial_queries)   → evidencia cruda
    2. reflect(evidence, goal)   → ¿qué gaps de información quedan?
    3. search(gap_queries)       → re-búsqueda dirigida
    4. repeat hasta max_cycles o sin gaps

El agente decide qué buscar siguiente (tool calling estructurado) basándose en
su propia reflexión sobre la cobertura del objetivo. Esto produce investigación
mucho más completa que el single-shot original.

Diseño: función pura reutilizable; el grafo la invoca. Sin deps nuevas (reutiliza
web_search + el helper _llm del módulo product_graph).
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ai_agents.tools.web_search_tool import search as web_search

logger = logging.getLogger(__name__)

DEFAULT_RESEARCH_CYCLES = 2  # search→reflect→search cuenta como 1 ciclo
MAX_RESEARCH_CYCLES = 4      # tope anti-bucle


@dataclass
class ResearchResult:
    """Resultado consolidado del deep research."""
    raw_text: str
    sources: List[str] = field(default_factory=list)
    cycles_run: int = 0
    queries_used: List[str] = field(default_factory=list)
    gaps_remaining: List[str] = field(default_factory=list)


def _llm_call(system: str, user: str) -> str:
    """Wrapper al helper _llm del product_graph (mismo router zero-cost)."""
    from ai_agents.graphs.product_graph import _llm
    return _llm(system, user, temperature=0.4)


def deep_research(
    goal: str,
    mega_prompt: str,
    *,
    max_cycles: int = DEFAULT_RESEARCH_CYCLES,
    llm_call=None,
    search_fn=None,
) -> ResearchResult:
    """
    Ejecuta investigación profunda multi-paso.

    Args:
        goal: objetivo del producto.
        mega_prompt: prompt de investigación inicial.
        max_cycles: nº de ciclos search→reflect (tope MAX_RESEARCH_CYCLES).
        llm_call: LLM inyectado (mock en tests). Default: router real.
        search_fn: función de búsqueda inyectada (mock en tests). Default: web_search.

    Returns:
        ResearchResult con evidencia consolidada, fuentes y metadatos.
    """
    llm = llm_call or _llm_call
    search = search_fn or web_search
    max_cycles = min(max_cycles, MAX_RESEARCH_CYCLES)

    # 1. Queries iniciales derivadas del mega_prompt.
    queries = _derive_initial_queries(goal, mega_prompt)
    all_sources: List[str] = []
    evidence_chunks: List[str] = []
    queries_used: List[str] = []
    cycles_run = 0
    gaps: List[str] = []

    for cycle in range(max_cycles):
        # --- SEARCH: ejecutar todas las queries pendientes ---
        for q in queries:
            queries_used.append(q)
            data = _search_with_retry(search, q, max_results=4)
            if data.get("available") and data.get("results"):
                for hit in data.get("results", []):
                    evidence_chunks.append(
                        f"[{hit.get('title','')}] {hit.get('snippet','')}"
                    )
                    if hit.get("url"):
                        all_sources.append(hit["url"])
            elif data.get("available") and not data.get("results"):
                # WEB_SEARCH_EMPTY: backend respondió pero sin hits (anti-bot).
                evidence_chunks.append(f"(sin hits web para: {q} — posible anti-bot)")
            else:
                evidence_chunks.append(f"(web no disponible para: {q})")

        evidence = "\n".join(evidence_chunks) or "(sin evidencia web — usando conocimiento paramétrico)"
        cycles_run += 1

        # --- REFLECT: ¿qué gaps quedan? ---
        reflection = _reflect(llm, goal, mega_prompt, evidence, cycle, gaps)

        # Si no hay gaps nuevos o es el último ciclo, terminar.
        new_queries = reflection.get("gap_queries", [])
        new_gaps = reflection.get("gaps", [])
        if not new_queries:
            gaps = new_gaps
            break

        queries = new_queries[:3]  # tope de queries por ciclo
        gaps = new_gaps

    # --- SYNTHESIZE: consolidar toda la evidencia en un informe crudo ---
    final_evidence = "\n".join(evidence_chunks)
    raw_text = _synthesize(llm, goal, mega_prompt, final_evidence, all_sources)

    return ResearchResult(
        raw_text=raw_text,
        sources=_dedupe(all_sources),
        cycles_run=cycles_run,
        queries_used=queries_used,
        gaps_remaining=gaps,
    )


# ============================================================
# Internal steps
# ============================================================

def _search_with_retry(search, query: str, *, max_results: int = 4, retries: int = 2):
    """
    Ejecuta una búsqueda reintentando si el backend responde WEB_SEARCH_EMPTY
    (rate-limit / anti-bot transitorio de DDG).

    Backoff: 1s, 2s entre reintentos. En tests search_fn es un mock que no
    duerme (time.sleep se patchea o el mock devuelve de inmediato).
    """
    last = {"available": False, "results": [], "sources": []}
    for attempt in range(retries + 1):
        data = search(query, max_results=max_results)
        last = data
        # Si hay resultados o el backend no está disponible, no reintentar.
        if data.get("results") or not data.get("available"):
            return data
        # WEB_SEARCH_EMPTY: reintentar con backoff (excepto en el último intento).
        if attempt < retries:
            # message contiene WEB_SEARCH_EMPTY cuando respondió pero sin hits.
            msg = data.get("message", "")
            if "WEB_SEARCH_EMPTY" in msg or "rate-limit" in msg.lower():
                time.sleep(2 ** attempt)  # 1s, 2s
                continue
        return data
    return last


def _derive_initial_queries(goal: str, mega_prompt: str) -> List[str]:
    """Queries iniciales: el objetivo + frases del mega_prompt."""
    qs = [goal.strip()] if goal.strip() else ["market trends"]
    for sentence in __import__("re").split(r"[;\n]", mega_prompt or ""):
        s = sentence.strip()
        if 15 <= len(s) <= 120:
            qs.append(s)
        if len(qs) >= 3:
            break
    return qs[:3]


def _reflect(llm, goal, mega_prompt, evidence, cycle, prev_gaps) -> Dict[str, Any]:
    """Pide al LLM que reflexione sobre gaps y proponga nuevas queries."""
    system = (
        "Eres un analista de investigación reflexivo. Dado un objetivo y evidencia "
        "recogida, identifica qué información CRÍTICA falta (gaps) y propón queries "
        "de búsqueda concretas para cubrirla. Responde SOLO JSON: "
        '{"gaps": [str], "gap_queries": [str]}. Si la cobertura es suficiente, '
        'devuelve arrays vacíos.'
    )
    user = (
        f"OBJETIVO: {goal}\n\n"
        f"PROMPT INICIAL:\n{mega_prompt}\n\n"
        f"EVIDENCIA RECOPILADA (ciclo {cycle}):\n{evidence[:2500]}\n\n"
        f"GAPS PREVIOS: {prev_gaps}\n\n"
        "¿Qué falta? Propón hasta 3 queries para el próximo ciclo (o [] si basta)."
    )
    raw = llm(system, user)
    return _safe_json_obj(raw)


def _synthesize(llm, goal, mega_prompt, evidence, sources) -> str:
    """Consolida toda la evidencia en un informe de investigación estructurado."""
    system = (
        "Eres un analista de investigación senior. Sintetiza evidencia en un "
        "informe estructurado en Markdown con secciones: Mercado, Tendencias, "
        "Competidores, Tecnologías clave, Riesgos. Cita fuentes cuando existan."
    )
    user = (
        f"OBJETIVO: {goal}\n\nPROMPT:\n{mega_prompt}\n\n"
        f"EVIDENCIA CONSOLIDADA:\n{evidence[:3500]}\n\n"
        f"FUENTES:\n{chr(10).join(sources[:15])}\n\nRedacta el informe."
    )
    return llm(system, user)


def _safe_json_obj(raw: str) -> Dict[str, Any]:
    """Extrae robustamente un objeto JSON de una respuesta LLM."""
    if not raw:
        return {"gaps": [], "gap_queries": []}
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass
    start, end = raw.find("{"), raw.rfind("}")
    if start != -1 and end > start:
        try:
            obj = json.loads(raw[start:end + 1])
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass
    return {"gaps": [], "gap_queries": []}


def _dedupe(items: List[str]) -> List[str]:
    """Elimina duplicados preservando orden."""
    seen = set()
    out = []
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out
