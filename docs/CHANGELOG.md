# Changelog

Todos los cambios notables del ProductGraph y del repositorio VeriAgent.

## [v2.0] — 2026-07-28 (Plan V2 completado)

ProductGraph evolucionado a sistema productivo: persistencia, streaming,
investigación multi-paso, rúbrica, API, guardrails de coste y evaluación de
regresión.

### Persistencia & ejecución
- `ai_agents/graphs/runtime.py`: checkpointing en memoria + persistencia a disco
  (state.json + report.md), `run_streaming()` con eventos por nodo, `list_runs`.
- `ai_agents/graphs/cli.py`: CLI completo (`run`, `stream`, `list`, `show`).

### Investigación profunda & rúbrica
- `ai_agents/graphs/deep_research.py`: bucle research→reflect→search con hasta
  N ciclos; el agente decide qué buscar según su reflexión.
- `ai_agents/graphs/critic_rubric.py`: rúbrica multi-eje (completitud, realismo,
  originalidad, accionabilidad) + `FeedbackMemory` persistente entre runs.

### Integración backend & guardrails
- `ai_agents/graphs/cost_guard.py`: `BudgetTracker` + `budgeted_run` aborta con
  `budget_exceeded` al superar el tope de tokens.
- `ai_agents/graphs/jobs.py`: job store async (thread-safe) para ejecutar el
  grafo en background.
- Endpoints `POST/GET /api/v1/product-graph/runs`, `/health`, `/dashboard`.

### Calidad & regresión
- `ai_agents/eval/regression_eval.py`: golden dataset de 5 specs, eval de
  regresión (cobertura de keywords + similitud léxica Jaccard), `DegradationMonitor`.

### Observabilidad
- `ai_agents/graphs/telemetry.py`: ahora captura tokens REALES del router
  (prompt/completion/total) vía `router.chat()` cuando está disponible.
- `/api/v1/product-graph/dashboard`: histórico con scores, tokens y coste.

### Tests
- +69 tests (327 total, 0 fallos).

---

## [v1.0] — 2026-07-28 (Plan V1 completado)

Estabilización de la base + entrega del ProductGraph inicial.

- ProductGraph: grafo Generator→Critic→Planner con loop de auto-mejora.
- WebSearchTool (DuckDuckGo, zero-cost).
- Fix de 10 tests en rojo + colección pytest desbloqueada.
- DDL ampliado (webhooks, sessions), firma XAdES real, webhooks durable con retry.
- Provisioner DB-per-tenant, 2FA persistente, rate limiting, security audit pytest.
- Deploy Docker/Compose robusto.
