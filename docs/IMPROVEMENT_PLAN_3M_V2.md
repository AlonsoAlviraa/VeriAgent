# Plan de Mejora de 3 Meses V2 — ProductGraph a Producción

**Fecha de baseline:** 2026-07-28 (tras completar el plan V1)
**Horizonte:** 12 semanas (3 meses) · **Cadencia:** 6 sprints quincenales
**Foco:** Evolucionar el `ProductGraph` (entregado en V1) hacia un sistema de generación de specs de producto **productivo, observable y robusto**.

Este documento es la continuación directa de `IMPROVEMENT_PLAN_3M.md` (V1, completado). Mientras V1 estabilizó la base del repo y entregó el grafo, V2 lo dota de: persistencia, streaming, investigación multi-paso real, critic con rúbrica, API endpoint, guardrails de coste y evaluación de regresión.

---

## 0. Estado actual (baseline V2)

Tras V1, el `ProductGraph` existe y funciona pero tiene limitaciones de producción:

| Área | Estado V1 | Gap para producción (V2) |
|------|-----------|--------------------------|
| Ejecución | `app.invoke()` síncrono, estado efímero | Sin checkpointing: una caída pierde todo el progreso; no se puede resumir. |
| Salida | `final_report` en memoria | Sin artifacts a disco; sin CLI para ejecutar y guardar. |
| Researcher | Single-shot (1 web search + 1 síntesis LLM) | No hay bucle research→reflect→search; no hay tool calling estructurado. |
| Critic | Score único 0-10 + feedback texto | Sin rúbrica multi-eje (completitud/realismo/originalidad/acionabilidad separados); sin memoria entre runs. |
| Integración | Solo ejecutable `__main__` | Sin endpoint API para dispararlo desde el backend; sin cola de jobs. |
| Coste | Router zero-cost, sin límites por run | Sin guardrails: un run con max_iterations=6 puede consumir tokens sin tope. |
| Calidad | eval de consistencia del critic | Sin golden dataset de specs de referencia; sin eval de regresión. |
| Observabilidad | Telemetría captura llamadas pero no tokens reales | La telemetría no se conecta al `usage` real del router. |

**Stack confirmado:** LangGraph 1.0.5 con `MemorySaver` (checkpointer en memoria disponible).

---

## A. Roadmap (12 semanas)

### Sprint 1–2 (Mes 1) — Persistencia + UX de ejecución ✅ COMPLETADO
- [x] **Checkpointing LangGraph**: wrapper `run_persistent()` con `MemorySaver` (resumir/reintentar runs por `thread_id`).
- [x] **Checkpointer a disco** (JSON): persistencia real entre procesos sin deps pesadas (`runs/<id>/state.json` + `report.md`).
- [x] **Streaming de resultados**: `run_streaming()` emite `RunEvent` por nodo (para UI/observabilidad).
- [x] **CLI/TUI del grafo**: `python -m ai_agents.graphs.cli {run|stream|list|show}` con flags.
- [x] **Artifacts a disco**: `final_report.md` + `state.json` en `runs/<id>/`.

### Sprint 3–4 (Mes 1→2) — Research profundo + critic con rúbrica ✅ COMPLETADO
- [x] **Researcher multi-paso**: bucle `research → reflect → search_again` (hasta MAX_RESEARCH_CYCLES=4) en `deep_research.py`.
- [x] **Tool calling estructurado**: el researcher decide qué buscar siguiente basándose en su reflexión sobre gaps.
- [x] **Critic con rúbrica multi-eje**: 4 scores separados (completitud/realismo/originalidad/acionabilidad) + global agregado por pesos en `critic_rubric.py`.
- [x] **Memoria/learning entre runs**: `FeedbackMemory` persistente de patrones de feedback recurrentes (capped a 100).

### Sprint 5–6 (Mes 2) — Integración backend + guardrails ✅ COMPLETADO
- [x] **API endpoint** `POST /api/v1/product-graph/runs` (202 async) para disparar el grafo.
- [x] **Cola de jobs**: `GET /api/v1/product-graph/runs/{id}` para estado + resultado; `GET /runs` histórico.
- [x] **Guardrails de coste**: `BudgetTracker` + `budgeted_run` aborta con `status="budget_exceeded"` al exceder tokens.
- [x] **Job store async** thread-safe (`GraphJobStore`) con background threads.

### Sprint 7–9 (Mes 2→3) — Calidad + regresión ✅ COMPLETADO
- [x] **Golden dataset**: 5 specs de referencia (saas/fintech/health/edtech/marketplace) con scores y keywords esperados.
- [x] **Eval de regresión**: cobertura de keywords + similitud léxica (Jaccard) + score delta.
- [x] **Detección de degradación**: `DegradationMonitor` compara scores recientes contra baseline persistente.

### Sprint 10–12 (Mes 3) — Observabilidad real + release ✅ COMPLETADO
- [x] **Telemetría con tokens reales**: wire a `router.chat()` para capturar `usage` (prompt/completion/total tokens por llamada).
- [x] **Dashboard de runs**: `GET /api/v1/product-graph/dashboard` (histórico con avg_score, tokens, coste $0.00).
- [x] **Health endpoint** del grafo (`/api/v1/product-graph/health`).
- [x] **Release v2.0**: `docs/CHANGELOG.md` con el grafo productivo.

---

## B. Métricas de éxito V2 — RESULTADO REAL

| Métrica | Baseline V2 | Objetivo Mes 3 | **Resultado real** |
|---------|-------------|-----------------|---------------------|
| Tests en verde | 258 | ≥ 310, 0 fallos | **327, 0 fallos** ✅ |
| Runs reanudables | No | Sí (checkpoint) | **Sí (MemorySaver + disco)** ✅ |
| Streaming | No | Sí (eventos por nodo) | **Sí (`run_streaming`)** ✅ |
| Ejes del critic | 1 (score global) | 4 (rúbrica) | **4 (rúbrica ponderada)** ✅ |
| Endpoint API grafo | No | Sí (run + status) | **Sí (run/status/list/health/dashboard)** ✅ |
| Guardrail coste | No | Sí (budget por run) | **Sí (BudgetTracker + abort)** ✅ |
| Golden dataset | 0 | ≥ 5 specs | **5 specs** ✅ |
| Tokens trazados | Conteo de llamadas | Tokens reales del router | **Tokens reales vía router.chat()** ✅ |

---

## C. Riesgos y mitigaciones

| Riesgo | Mitigación |
|--------|------------|
| Checkpointer sqlite añade dep pesada | Checkpointer propio a disco (JSON), sin deps extra. |
| Researcher multi-paso dispara coste | Budget guardrail (Sprint 5-6) + límite de ciclos de research. |
| Golden dataset subjetivo | Múltiples referencias + similitud semántica, no exact match. |
| Tests de regresión flaky (LLM no determinista) | Mocks deterministas en CI; eval con LLM real solo manual. |

---

*Plan V2. Ejecución sprint a sprint, sin human-in-the-loop.*
