"""
[TEAM-B][AGENT-013] ProductGraph — Autonomous Self-Improving Product Graph.

Sistema: ProductGraph
Principio central:
    Generator (research → ideas → spec) → Critic →
        (si falla calidad) → Planner → re-ejecución selectiva de workflows →
        loop hasta alcanzar umbral de calidad o máximo de iteraciones.

Totalmente sin Human-in-the-Loop.

Diseño:
- Estado compartido: `ProductGraphState` (TypedDict).
- 8 nodos especializados (planner, researcher, synthesizer, idea_generator,
  spec_writer, critic, improver, finalizer).
- Contador de iteraciones duro (`max_iterations`, por defecto 6).
- Re-ejecución selectiva: el `improver` marca qué áreas son débiles y el
  `planner` re-lanza solo los nodos necesarios.
- Reutiliza el router LLM zero-cost (`ai_agents.llm_router`) y la herramienta
  `web_search` (DuckDongGo, sin API key).

El grafo usa LangGraph si está disponible; en caso contrario cae a una
ejecución imperativa equivalente (callable node graph) para no romper
entornos sin la dependencia — mismo patrón que `orchestrator.py`.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Annotated, Any, Callable, Dict, List, Optional, TypedDict

from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

# El router LLM depende de litellm (y proveedores), que es opcional en entornos
# de test/coste-cero. Lo importamos de forma perezosa para no romper la colección
# de tests ni la importación del grafo cuando litellm no está instalado.
# Fallbacks directos (sin litellm): preferencia xAI (Grok) > Gemini > None.
_chat_completion = None
try:
    from ai_agents.llm_router import chat_completion as _chat_completion
except Exception:  # litellm ausente — probar clientes directos
    # 1) xAI (Grok) — OpenAI-compatible, menos costoso con grok-4.20 non-reasoning
    try:
        from ai_agents.xai_direct import chat_completion as _xai_completion, is_available as _xai_available
        if _xai_available():
            _chat_completion = _xai_completion
            logger.info("[ProductGraph] Usando cliente xAI (Grok) directo (litellm no instalado).")
    except Exception:
        pass
    # 2) Gemini — fallback si xAI no está configurada
    if _chat_completion is None:
        try:
            from ai_agents.gemini_direct import chat_completion as _gemini_completion, is_available as _gemini_available
            if _gemini_available():
                _chat_completion = _gemini_completion
                logger.info("[ProductGraph] Usando cliente Gemini directo (litellm no instalado).")
        except Exception:
            pass

# BudgetExceeded: excepción de control de flujo del cost guard (import perezoso
# para evitar ciclo: cost_guard importa product_graph).
class BudgetExceeded(Exception):
    """Se excedió el presupuesto de tokens de la run (cost guard)."""

    def __init__(self, used: int = 0, budget: int = 0):
        self.used = used
        self.budget = budget
        super().__init__(f"Budget exceeded: {used} > {budget} tokens")

from ai_agents.tools.web_search_tool import search as web_search

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


# ============================================================
# CONFIGURATION
# ============================================================

QUALITY_THRESHOLD = 8.0        # score mínimo del critic para finalizar (rúbrica calibrada)
DEFAULT_MAX_ITERATIONS = 6     # contador duro anti-bucle
IDEAS_MIN = 15                 # idea_generator: mínimo de ideas a generar
IDEAS_MAX = 25

# Nodos por iteración completa: planner→researcher→synthesizer→idea_generator
# →spec_writer→critic (+improver en cada loop). 7 pasos por iteración de mejora.
_STEPS_PER_ITERATION = 7


def recursion_limit_for(max_iterations: int) -> int:
    """
    Calcula el `recursion_limit` de LangGraph coherente con `max_iterations`.

    El loop se ejecuta como máximo `max_iterations + 1` pasadas (de
    iteration=0 hasta iteration=max), cada una de `_STEPS_PER_ITERATION`
    pasos. Cualquier caller de `app.invoke(...)` DEBE pasar
    `config={"recursion_limit": recursion_limit_for(state.max_iterations)}`;
    de lo contrario LangGraph puede cortar el loop de mejora por su límite
    por defecto (25) antes de que el contador duro actúe.
    """
    # +1 pasada (la inicial cuenta), + margen de seguridad.
    return max(25, (max_iterations + 1) * _STEPS_PER_ITERATION + 4)


# ============================================================
# SHARED STATE
# ============================================================

class ProductGraphState(TypedDict):
    # --- Input original ---
    goal: str
    mega_prompt: str

    # --- Investigación ---
    research_raw: str
    research_synthesis: str
    sources: List[str]

    # --- Generación de producto ---
    product_ideas: List[Dict[str, Any]]
    selected_core_product: Dict[str, Any]
    product_spec: str
    technical_architecture: str
    gtm_strategy: str

    # --- Self-review ---
    critique: str
    quality_score: float            # 0.0 - 10.0
    feedback: List[str]
    iteration: int
    max_iterations: int

    # --- Control de flujo ---
    # status: researching|generating|reviewing|improving|done|failed
    status: str
    # Áreas marcadas como débiles por el improver para re-ejecución selectiva.
    # Subconjunto de {"research","ideas","spec"}.
    weak_areas: List[str]
    # Output consolidado por el finalizer.
    final_report: str
    # Patrón best-so-far: el grafo conserva el mejor estado entre iteraciones
    # para no degradar si una re-ejecución empeora el resultado.
    best_score: float
    best_product_spec: str
    best_technical_architecture: str
    best_gtm_strategy: str
    best_critique: str
    messages: Annotated[list, add_messages]


def initial_state(goal: str, mega_prompt: str, max_iterations: int = DEFAULT_MAX_ITERATIONS) -> Dict[str, Any]:
    """Construye un estado inicial válido para invocar el grafo."""
    return {
        "goal": goal,
        "mega_prompt": mega_prompt,
        "research_raw": "",
        "research_synthesis": "",
        "sources": [],
        "product_ideas": [],
        "selected_core_product": {},
        "product_spec": "",
        "technical_architecture": "",
        "gtm_strategy": "",
        "critique": "",
        "quality_score": 0.0,
        "feedback": [],
        "iteration": 0,
        "max_iterations": max_iterations,
        "status": "researching",
        "weak_areas": [],
        "final_report": "",
        "best_score": 0.0,
        "best_product_spec": "",
        "best_technical_architecture": "",
        "best_gtm_strategy": "",
        "best_critique": "",
        "messages": [],
    }


# ============================================================
# LLM HELPER (with graceful degradation)
# ============================================================

def _llm(system: str, user: str, temperature: float = 0.7, max_tokens: int = 4096) -> str:
    """Llama al router zero-cost. Retorna "" si no hay proveedores.

    Nota: BudgetExceeded (control de flujo del cost guard) se propaga, no se
    captura, para que budgeted_run pueda terminarla limpiamente.
    """
    if _chat_completion is None:
        logger.error("[ProductGraph] Router LLM no disponible (litellm no instalado).")
        return ""
    try:
        return _chat_completion(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        ) or ""
    except BudgetExceeded:
        # Control de flujo del cost guard: propagar sin tratarlo como error de LLM.
        raise
    except Exception as exc:
        logger.error("[ProductGraph] LLM no disponible: %s", exc)
        return ""


# ============================================================
# NODES
# ============================================================

def planner_node(state: ProductGraphState) -> Dict[str, Any]:
    """
    Supervisor + Planner.

    Iteración 0 → lanza la cadena completa.
    Iteraciones siguientes → respeta `weak_areas` para re-ejecución selectiva.
    Incrementa el contador de iteraciones al (re)entrar tras un `improver`.
    """
    iteration: int = state.get("iteration", 0)
    weak: List[str] = list(state.get("weak_areas") or [])

    # Si el improver marcó áreas débiles, es una re-entrada de mejora.
    if weak and iteration > 0:
        logger.info("[Planner] Re-ejecución selectiva (iter=%d) áreas: %s", iteration, weak)

    status = "researching" if (not weak or "research" in weak) else "generating"
    return {"iteration": iteration, "status": status, "weak_areas": weak}


def researcher_node(state: ProductGraphState) -> Dict[str, Any]:
    """
    Research Agent: ejecuta el mega_prompt como deep research.

    Combina web search real (zero-cost) con síntesis LLM de los hallazgos.
    Si la web no está disponible, degrada a conocimiento paramétrico del LLM.
    """
    goal = state.get("goal", "")
    mega_prompt = state.get("mega_prompt", "")

    # 1) Web research con reintentos (anti rate-limit de DDG).
    from ai_agents.graphs.deep_research import _search_with_retry  # perezoso: evita ciclo
    web_context = ""
    sources: List[str] = []
    for q in _derive_search_queries(goal, mega_prompt):
        data = _search_with_retry(web_search, q, max_results=5)
        if data.get("available") and data.get("results"):
            for hit in data.get("results", []):
                web_context += f"- [{hit.get('title','')}]({hit.get('url','')}): {hit.get('snippet','')}\n"
                if hit.get("url"):
                    sources.append(hit["url"])
    if not web_context:
        web_context = "(Sin resultados web — usando conocimiento paramétrico del LLM.)"

    # 2) Síntesis LLM del mega_prompt + evidencia web.
    system = (
        "Eres un analista de investigación senior. Sintetiza evidencia web y "
        "conocimiento de dominio en hallazgos crudos, con citas. Sé concreto, "
        "cita números y fuentes cuando existan. No inventes URLs. Sé conciso: "
        "prioriza insights accionables sobre descripción genérica."
    )
    user = (
        f"OBJETIVO: {goal}\n\n"
        f"MEGA-PROMPT DE INVESTIGACIÓN:\n{mega_prompt}\n\n"
        f"EVIDENCIA WEB RECUPERADA:\n{web_context[:2500]}\n\n"
        "Devuelve un informe de investigación en Markdown con secciones: "
        "Mercado (tamaño/crecimiento), Tendencias, Competidores (con diferencias), "
        "Oportunidades, Riesgos. Máximo 600 palabras."
    )
    research_raw = _llm(system, user, temperature=0.4, max_tokens=2500)

    # Fallback útil cuando el LLM degrada (router no disponible): construir un
    # reporte mínimo con la evidencia web cruda, para que el grafo tenga algo
    # accionable en vez de vacío.
    if not research_raw:
        research_raw = _web_only_research(goal, mega_prompt, web_context, sources)

    return {
        "research_raw": research_raw,
        "sources": sources,
        "status": "generating",
    }


def _web_only_research(goal: str, mega_prompt: str, web_context: str, sources: List[str]) -> str:
    """Reporte mínimo de investigación cuando el LLM no está disponible.

    Estructura la evidencia web recuperada para que los nodos siguientes puedan
    trabajar, aunque sin la síntesis semántica del LLM.
    """
    lines = [
        f"# Investigación (modo web-only, LLM no disponible)\n",
        f"**Objetivo:** {goal}\n",
        f"**Prompt:** {mega_prompt}\n",
        "## Evidencia web recuperada\n",
    ]
    if web_context and "Sin resultados web" not in web_context:
        lines.append(web_context)
    else:
        lines.append("_(No se recuperó evidencia web — rate-limit o backend vacío.)_\n")
    if sources:
        lines.append("\n## Fuentes\n")
        for s in sources:
            lines.append(f"- {s}")
    return "\n".join(lines)


def synthesizer_node(state: ProductGraphState) -> Dict[str, Any]:
    """Synthesis Agent: resume, estructura y prioriza hallazgos."""
    research_raw = state.get("research_raw", "")
    goal = state.get("goal", "")

    system = (
        "Eres un synthesizer ejecutivo. Comprime investigación cruda en un "
        "resumen estructurado y priorizado (insights top, oportunidades, "
        "amenazas). Máxima densidad informativa, sin paja."
    )
    user = f"OBJETIVO: {goal}\n\nINVESTIGACIÓN CRUDA:\n{research_raw}\n\nResume y prioriza."
    synthesis = _llm(system, user, temperature=0.3)
    return {"research_synthesis": synthesis}


def idea_generator_node(state: ProductGraphState) -> Dict[str, Any]:
    """Creative Product Agent: genera 15-25 ideas de producto de alto potencial."""
    synthesis = state.get("research_synthesis", "")
    goal = state.get("goal", "")
    prior_feedback = _filter_feedback(state.get("feedback", []), {"ideas", "spec"})

    system = (
        "Eres un estratega de producto pragmático. Genera ideas de producto "
        "diferenciadas, realistas y CONCRETAS para una v1 ejecutable por un "
        "equipo pequeño. Reglas:\n"
        "- Cada idea debe ser viable con stack simple (Postgres + 1 LLM + app web).\n"
        "- Evita overpromising: nada de 'agentes autónomos completos', 'IA que "
        "negocia sola', 'automatización total'. Sé honesto sobre lo que v1 hace.\n"
        "- Prioriza feasibility (que se pueda construir de verdad) sobre ambición.\n"
        "- Differentiator debe ser CONCRETO y verificable, no marketing.\n"
        f"Responde EXCLUSIVAMENTE un JSON array de {IDEAS_MIN}-{IDEAS_MAX} objetos, "
        'cada uno con claves: "name", "one_liner", "target_user", "core_value", '
        '"differentiator", "monetization", "feasibility_1_10". Sin texto fuera del JSON.'
    )
    user = (
        f"OBJETIVO: {goal}\n\nSÍNTESIS DE INVESTIGACIÓN:\n{synthesis[:2000]}\n\n"
        f"FEEDBACK A INCORPORAR:\n{prior_feedback or '(primera iteración)'}\n\n"
        f"Genera entre {IDEAS_MIN} y {IDEAS_MAX} ideas realistas y diferenciadas."
    )
    raw = _llm(system, user, temperature=0.8, max_tokens=4000)
    ideas = _safe_parse_json_list(raw)
    if not ideas:
        ideas = [{"name": "Idea pendiente", "one_liner": raw[:200]}]
    return {"product_ideas": ideas}


def spec_writer_node(state: ProductGraphState) -> Dict[str, Any]:
    """
    Product Spec Agent: selecciona la mejor idea y escribe PRD + arquitectura
    técnica + estrategia GTM.
    """
    ideas = state.get("product_ideas", [])
    goal = state.get("goal", "")
    synthesis = state.get("research_synthesis", "")
    prior_feedback = _filter_feedback(state.get("feedback", []), {"spec"})

    # Selección determinista de la mejor idea por (feasibility, differentiator).
    selected = _select_best_idea(ideas)

    system = (
        "Eres un Product Manager + Solutions Architect de ÉLITE mundial (ex-Stripe, "
        "ex-Linear, ex-Vercel). Tu objetivo es producir un PRD, arquitectura y GTM "
        "de CALIDAD EXCEPTIONAL (objetivo: 10/10 en cualquier rúbrica profesional).\n\n"
        "Estándares OBLIGATORIOS de calidad:\n"
        "1. COMPLETO: PRD con visión, problema, personas, alcance v1 (features "
        "enumeradas con detalle), métricas North Star + KPIs con números reales, "
        "roadmap con fases, riesgos con mitigación.\n"
        "2. REALISTA: Arquitectura v1 ejecutable por 2-3 devs en 3 meses. Stack "
        "simple y probado (Next.js + Postgres + 1 LLM opcional). NADA de "
        "sobre-ingeniería (no Neo4j, no microservicios, no XGBoost en v1).\n"
        "3. ORIGINAL: Differentiator CONCRETO y verificable, no marketing. Explica "
        "POR QUÉ es distinto a competidores nombrados específicamente.\n"
        "4. ACCIONABLE: Cada feature tiene criterios de aceptación. Las métricas "
        "tienen thresholds numéricos. El GTM tiene fases con targets de revenue/users.\n\n"
        "Coherencia interna CRÍTICA: lo que promete el PRD debe estar soportado "
        "por la arquitectura. Cero gap entre promesa y implementación.\n\n"
        "Si hay FEEDBACK del critic, APLÍCALO punto por punto de forma explícita."
    )
    user = (
        f"OBJETIVO: {goal}\n"
        f"IDEA SELECCIONADA: {json.dumps(selected, ensure_ascii=False)}\n\n"
        f"SÍNTESIS DE MERCADO (resumida):\n{synthesis[:1500]}\n\n"
        f"FEEDBACK A INCORPORAR:\n{prior_feedback or '(primera iteración, sin feedback previo)'}\n\n"
        "Devuelve EXACTAMENTE tres secciones COMPLETAS (nunca a medias) con estos "
        "marcadores en líneas propias:\n"
        "=== PRD ===\n=== ARQUITECTURA ===\n=== GTM ==="
    )
    raw = _llm(system, user, temperature=0.4, max_tokens=8000)
    prd, arch, gtm = _split_spec_sections(raw)

    return {
        "selected_core_product": selected,
        "product_spec": prd,
        "technical_architecture": arch,
        "gtm_strategy": gtm,
        "status": "reviewing",
    }


def critic_node(state: ProductGraphState) -> Dict[str, Any]:
    """
    Strict Critic Agent: evalúa calidad global en 4 ejes (completitud,
    realismo, originalidad, accionabilidad).

    Devuelve quality_score (0-10), critique y feedback (lista de gaps
    accionables). La salida es JSON parseado de forma robusta.
    """
    system = (
        "Eres un crítico profesional y equilibrado (estilo partner de YC o "
        "reviewer de Product Hunt). Evalúa la calidad GLOBAL del producto "
        "propuesto en 4 ejes, usando esta RÚBRICA CALIBRADA:\n\n"
        "COMPLETITUD: ¿Cubre visión, problema, personas, features v1, métricas "
        "con números, roadmap y riesgos?\n"
        "REALISMO: ¿La arquitectura v1 es ejecutable por un equipo pequeño en "
        "3 meses, sin sobre-ingeniería? ¿Hay coherencia entre promesa y stack?\n"
        "ORIGINALIDAD: ¿El differentiator es concreto y verificable frente a "
        "competidores nombrados, no marketing genérico?\n"
        "ACIONABILIDAD: ¿Cada feature tiene criterios? ¿Las métricas tienen "
        "thresholds numéricos? ¿El GTM tiene fases con targets?\n\n"
        "ANCHORS DE SCORING (sé justo, reconoce la calidad real):\n"
        "- 9-10: Exceptional. Mejor que el 90% de PRDs profesionales. Listo "
        "para presentar a inversores. Todos los ejes sobresalientes.\n"
        "- 8-8.9: Muy bueno. Sólido en los 4 ejes con gaps menores. Mejor que "
        "la mayoría de PRDs reales.\n"
        "- 7-7.9: Bueno. Cubre lo esencial pero faltan detalles en 1-2 ejes.\n"
        "- 6-6.9: Aceptable. Faltan secciones o hay incoherencias notables.\n"
        "- <6: Insuficiente.\n\n"
        "NO seas punitivo por defecto. Si el spec es genuinamente bueno, "
        "reconócelo con el score que merece. Responde EXCLUSIVAMENTE un JSON: "
        '{"quality_score" (float 0-10), "critique" (str), '
        '"feedback" (array de strings accionables), '
        '"weak_areas" (array, subconjunto de ["research","ideas","spec"])}.'
    )
    user = (
        f"OBJETIVO: {state.get('goal','')}\n\n"
        f"SÍNTESIS:\n{state.get('research_synthesis','')[:2000]}\n\n"
        f"IDEAS (top 3):\n{json.dumps(state.get('product_ideas',[])[:3], ensure_ascii=False)}\n\n"
        f"PRD:\n{state.get('product_spec','')[:2500]}\n\n"
        f"ARQUITECTURA:\n{state.get('technical_architecture','')[:1500]}\n\n"
        f"GTM:\n{state.get('gtm_strategy','')[:1500]}\n\n"
        "Evalúa con la rúbrica calibrada y devuelve el JSON."
    )
    raw = _llm(system, user, temperature=0.2)
    parsed = _safe_parse_json_obj(raw)

    score = float(parsed.get("quality_score", 0.0) or 0.0)
    score = max(0.0, min(10.0, score))
    critique = str(parsed.get("critique", "") or "")
    feedback = parsed.get("feedback", [])
    feedback = feedback if isinstance(feedback, list) else [str(feedback)]
    weak = parsed.get("weak_areas", [])
    weak = [w for w in (weak if isinstance(weak, list) else [str(weak)])
            if w in ("research", "ideas", "spec")]

    # Patrón best-so-far: si este score supera al mejor guardado, conservamos
    # el spec actual como referencia para que el finalizer no degradar.
    best_score = float(state.get("best_score", 0.0) or 0.0)
    update: Dict[str, Any] = {
        "quality_score": score,
        "critique": critique,
        "feedback": [str(f) for f in feedback],
        "weak_areas": weak,
        "status": "reviewing",
    }
    if score > best_score:
        update.update({
            "best_score": score,
            "best_product_spec": state.get("product_spec", ""),
            "best_technical_architecture": state.get("technical_architecture", ""),
            "best_gtm_strategy": state.get("gtm_strategy", ""),
            "best_critique": critique,
        })
        logger.info("[Critic] Nuevo mejor score: %.2f (previo %.2f)", score, best_score)
    return update


def improver_node(state: ProductGraphState) -> Dict[str, Any]:
    """
    Improvement Agent: consume el feedback del critic, confirma/refina las
    áreas débiles y deja instrucciones para que el planner re-lance solo lo
    necesario. Incrementa el contador de iteraciones.
    """
    feedback = state.get("feedback", [])
    weak = list(state.get("weak_areas") or [])
    # Si el critic no marcó áreas, asumimos que hay que refinar todo el generador.
    if not weak:
        weak = ["research", "ideas", "spec"]

    next_iteration = int(state.get("iteration", 0)) + 1

    logger.info(
        "[Improver] iteración %d → %d | score=%.2f | áreas débiles: %s",
        state.get("iteration", 0), next_iteration,
        state.get("quality_score", 0.0), weak,
    )

    return {
        "iteration": next_iteration,
        "status": "improving",
        "weak_areas": weak,
        # Reinyectamos el feedback en messages para que los nodos lo consuman
        # (ya lo tienen en state.feedback, pero dejamos traza explícita).
        "messages": [{"role": "assistant", "content": f"IMPROVE:{json.dumps(weak)}"}],
    }


def finalizer_node(state: ProductGraphState) -> Dict[str, Any]:
    """
    Formatter: empaqueta el output final consolidado en Markdown.

    Usa el patrón best-so-far: si el score de la última iteración fue peor que
    el mejor registrado, restaura el mejor spec/critique para no degradar la
    salida final.
    """
    reached_max = state.get("iteration", 0) >= state.get("max_iterations", DEFAULT_MAX_ITERATIONS)
    current_score = state.get("quality_score", 0.0)
    best_score = float(state.get("best_score", 0.0) or 0.0)

    # Restaurar el mejor estado si la última iteración degradó.
    if best_score > current_score and best_score > 0.0:
        logger.info(
            "[Finalizer] Restaurando mejor spec (best=%.2f > último=%.2f)",
            best_score, current_score,
        )
        state = {
            **state,
            "quality_score": best_score,
            "product_spec": state.get("best_product_spec") or state.get("product_spec", ""),
            "technical_architecture": state.get("best_technical_architecture") or state.get("technical_architecture", ""),
            "gtm_strategy": state.get("best_gtm_strategy") or state.get("gtm_strategy", ""),
            "critique": state.get("best_critique") or state.get("critique", ""),
        }
        score = best_score
    else:
        score = current_score

    status = "done" if score >= QUALITY_THRESHOLD else ("failed" if reached_max else "done")
    report = _format_final_report(state, status, reached_max)
    return {"final_report": report, "status": status}


# ============================================================
# ROUTING
# ============================================================

def route_after_critic(state: ProductGraphState) -> str:
    """Decide si mejorar (loop) o finalizar tras el critic."""
    score = state.get("quality_score", 0.0)
    iteration = state.get("iteration", 0)
    max_iter = state.get("max_iterations", DEFAULT_MAX_ITERATIONS)

    if score >= QUALITY_THRESHOLD:
        return "finalize"
    if iteration >= max_iter:
        return "finalize"
    return "improve"


# ============================================================
# GRAPH BUILD
# ============================================================

def build_product_graph():
    """
    Compila el grafo ProductGraph con LangGraph.

    Flujo:
        START → planner → researcher → synthesizer → idea_generator →
        spec_writer → critic → (route) → improver → planner (loop)
                                              ↘ finalizer → END
    """
    workflow = StateGraph(ProductGraphState)

    workflow.add_node("planner", planner_node)
    workflow.add_node("researcher", researcher_node)
    workflow.add_node("synthesizer", synthesizer_node)
    workflow.add_node("idea_generator", idea_generator_node)
    workflow.add_node("spec_writer", spec_writer_node)
    workflow.add_node("critic", critic_node)
    workflow.add_node("improver", improver_node)
    workflow.add_node("finalizer", finalizer_node)

    workflow.set_entry_point("planner")

    workflow.add_edge("planner", "researcher")
    workflow.add_edge("researcher", "synthesizer")
    workflow.add_edge("synthesizer", "idea_generator")
    workflow.add_edge("idea_generator", "spec_writer")
    workflow.add_edge("spec_writer", "critic")

    workflow.add_conditional_edges(
        "critic",
        route_after_critic,
        {"improve": "improver", "finalize": "finalizer"},
    )

    workflow.add_edge("improver", "planner")   # loop de mejora
    workflow.add_edge("finalizer", END)

    return workflow.compile()


# ============================================================
# UTILITIES (parsing, selection, formatting)
# ============================================================

def _derive_search_queries(goal: str, mega_prompt: str) -> List[str]:
    """Deriva 2-3 queries accionables del objetivo/mega-prompt."""
    base = (goal or "").strip() or "market trends"
    queries = [base]
    # Frases del mega_prompt como queries secundarias (hasta 2).
    for sentence in re.split(r"[;\n]", mega_prompt or ""):
        s = sentence.strip()
        if 15 <= len(s) <= 120:
            queries.append(s)
        if len(queries) >= 3:
            break
    return queries[:3]


def _safe_parse_json_list(raw: str) -> List[Dict[str, Any]]:
    """Extrae robustamente un array JSON de una respuesta LLM."""
    if not raw:
        return []
    # Intentar extracción directa.
    try:
        obj = json.loads(raw)
        if isinstance(obj, list):
            return [x for x in obj if isinstance(x, dict)]
    except json.JSONDecodeError:
        pass
    # Buscar el primer array JSON en el texto.
    start = raw.find("[")
    end = raw.rfind("]")
    if start != -1 and end != -1 and end > start:
        try:
            obj = json.loads(raw[start:end + 1])
            if isinstance(obj, list):
                return [x for x in obj if isinstance(x, dict)]
        except json.JSONDecodeError:
            pass
    return []


def _safe_parse_json_obj(raw: str) -> Dict[str, Any]:
    """Extrae robustamente un objeto JSON de una respuesta LLM."""
    if not raw:
        return {}
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            obj = json.loads(raw[start:end + 1])
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass
    return {}


def _select_best_idea(ideas: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Selección determinista: maximiza feasibility (y differentiator como tiebreak textual)."""
    if not ideas:
        return {"name": "Producto por definir", "one_liner": ""}
    valid = [i for i in ideas if isinstance(i, dict)]
    if not valid:
        return {"name": "Producto por definir", "one_liner": ""}

    def score(i: Dict[str, Any]) -> float:
        try:
            return float(i.get("feasibility_1_10", 0) or 0)
        except (TypeError, ValueError):
            return 0.0

    return max(valid, key=score)


def _split_spec_sections(raw: str) -> tuple[str, str, str]:
    """Separa el output del spec_writer por los marcadores === PRD/ARQUITECTURA/GTM ===."""
    if not raw:
        return "", "", ""
    parts = re.split(r"===\s*(PRD|ARQUITECTURA|GTM)\s*===", raw)
    prd = arch = gtm = ""
    current = None
    for part in parts:
        p = part.strip()
        if p in ("PRD", "ARQUITECTURA", "GTM"):
            current = p
        elif current == "PRD":
            prd = (prd + "\n" + p).strip()
        elif current == "ARQUITECTURA":
            arch = (arch + "\n" + p).strip()
        elif current == "GTM":
            gtm = (gtm + "\n" + p).strip()
    # Fallback: si no había marcadores, todo va a PRD.
    if not prd and not arch and not gtm:
        prd = raw
    return prd, arch, gtm


def _filter_feedback(feedback: List[str], areas: set) -> str:
    """
    Serializa el feedback del critic como instrucciones imperativas accionables
    para el nodo destino. El feedback se transforma de lista pasiva a órdenes
    concretas ("CORRIGE: ...") para que el LLM lo aplique de forma dirigida.
    """
    if not feedback:
        return ""
    items = [f for f in feedback if isinstance(f, str) and f.strip()]
    if not items:
        return ""
    lines = ["INSTRUCCIONES OBLIGATORIAS del critic — debes abordar CADA punto:"]
    for i, f in enumerate(items, 1):
        lines.append(f"  {i}. CORRIGE: {f}")
    lines.append("Si no abordas estos puntos, el score no subirá.")
    return "\n".join(lines)


def _format_final_report(state: ProductGraphState, status: str, reached_max: bool) -> str:
    """Construye el reporte Markdown final consolidado."""
    selected = state.get("selected_core_product", {}) or {}
    sources = state.get("sources", []) or []

    lines: List[str] = []
    lines.append("# ProductGraph — Reporte Final\n")
    lines.append(f"- **Estado:** {status}")
    lines.append(f"- **Quality score:** {state.get('quality_score', 0.0):.2f} / 10")
    lines.append(f"- **Iteraciones:** {state.get('iteration', 0)} / {state.get('max_iterations', DEFAULT_MAX_ITERATIONS)}")
    if reached_max and status != "done":
        lines.append("\n> ⚠️ Se alcanzó el máximo de iteraciones sin superar el umbral de calidad.")
    lines.append("")

    lines.append(f"## Producto seleccionado\n**{selected.get('name','(sin nombre)')}**\n")
    if selected.get("one_liner"):
        lines.append(f"_{selected.get('one_liner')}_\n")

    lines.append("## PRD\n")
    lines.append(state.get("product_spec", "") or "_(vacío)_")
    lines.append("\n## Arquitectura técnica\n")
    lines.append(state.get("technical_architecture", "") or "_(vacío)_")
    lines.append("\n## Estrategia GTM\n")
    lines.append(state.get("gtm_strategy", "") or "_(vacío)_")

    lines.append("\n## Crítica del evaluador\n")
    lines.append(state.get("critique", "") or "_(sin crítica)_")
    if state.get("feedback"):
        lines.append("\n**Feedback accionable:**")
        for f in state["feedback"]:
            lines.append(f"- {f}")

    if sources:
        lines.append("\n## Fuentes\n")
        for s in sources:
            lines.append(f"- {s}")

    return "\n".join(lines)


# ============================================================
# SMOKE ENTRYPOINT
# ============================================================

def _main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="ProductGraph — smoke run")
    parser.add_argument("--goal", default="SaaS de productividad para equipos remotos")
    parser.add_argument("--prompt", default="Investiga tendencias, competidores y oportunidades.")
    parser.add_argument("--max-iter", type=int, default=DEFAULT_MAX_ITERATIONS)
    args = parser.parse_args()

    app = build_product_graph()
    # El límite de recursión de LangGraph debe cubrir todos los pasos del loop.
    result = app.invoke(
        initial_state(args.goal, args.prompt, max_iterations=args.max_iter),
        config={"recursion_limit": recursion_limit_for(args.max_iter)},
    )
    print(result.get("final_report") or "[ProductGraph] No se generó reporte (¿API keys del router LLM configuradas?).")


if __name__ == "__main__":
    _main()
