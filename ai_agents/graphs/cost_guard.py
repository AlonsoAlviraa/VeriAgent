"""
[AGENT-019 / Sprint 5-V2] Cost guardrails para ProductGraph.

Budget tracker que aborta una run si excede el presupuesto de tokens. Se integra
como middleware del grafo: envuelve `_chat_completion` para acumular tokens y
lanza `BudgetExceeded` al superar el límite.

Diseño:
- `BudgetTracker`: acumula tokens consumidos por una run; `check()` lanza si excede.
- `budgeted_run()`: ejecuta el grafo dentro de un contexto con budget; al
  excederse, el grafo termina con `status="budget_exceeded"` en vez de colgar.
- Sin deps nuevas; reutiliza el router.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, Optional
from unittest.mock import patch

from ai_agents.graphs.product_graph import (
    DEFAULT_MAX_ITERATIONS,
    BudgetExceeded,
    build_product_graph,
    initial_state,
    recursion_limit_for,
)

logger = logging.getLogger(__name__)

# Budget por defecto: 50K tokens por run (suficiente para ~6 iteraciones de un
# grafo con prompts moderados). 0 = ilimitado.
DEFAULT_TOKEN_BUDGET = 50_000


@dataclass
class BudgetTracker:
    """Acumulador de tokens consumidos con límite."""
    budget: int = DEFAULT_TOKEN_BUDGET
    used: int = 0
    call_count: int = 0
    aborted: bool = False

    def consume(self, tokens: int) -> None:
        """Registra tokens consumidos; aborta si excede el budget."""
        self.used += max(0, int(tokens))
        self.call_count += 1
        if self.budget > 0 and self.used > self.budget:
            self.aborted = True
            raise BudgetExceeded(self.used, self.budget)

    @property
    def remaining(self) -> int:
        if self.budget <= 0:
            return -1  # ilimitado
        return max(0, self.budget - self.used)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "budget": self.budget,
            "used": self.used,
            "remaining": self.remaining,
            "call_count": self.call_count,
            "aborted": self.aborted,
        }


@contextmanager
def budgeted_llm(tracker: BudgetTracker, llm_call=None) -> Iterator[None]:
    """
    Context manager que envuelve _chat_completion para trackear tokens.

    Estima tokens por llamada (~4 chars/token) cuando el router no devuelve
    usage real. En tests se inyecta un llm_call con conteo determinista.

    Args:
        tracker: el BudgetTracker de la run.
        llm_call: LLM inyectado (mock). Default: router real.
    """
    target = llm_call
    if target is None:
        from ai_agents.graphs.product_graph import _chat_completion as _real
        target = _real

    def wrapper(messages, temperature=0.7, max_tokens=4096, **kwargs):
        # Estimar tokens de entrada (~4 chars/token).
        in_text = "".join(m.get("content", "") for m in messages)
        in_tokens = max(1, len(in_text) // 4)
        # Ejecutar antes de consumir para poder capturar output.
        content = target(messages, temperature=temperature, max_tokens=max_tokens, **kwargs)
        out_tokens = max(1, len(content or "") // 4)
        tracker.consume(in_tokens + out_tokens)
        return content

    with patch("ai_agents.graphs.product_graph._chat_completion", side_effect=wrapper):
        yield


def budgeted_run(
    goal: str,
    mega_prompt: str,
    *,
    budget: int = DEFAULT_TOKEN_BUDGET,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
    llm_call=None,
    no_web: bool = False,
) -> Dict[str, Any]:
    """
    Ejecuta el grafo con un budget de tokens. Si se excede, termina con
    status="budget_exceeded" y el progreso parcial.

    Returns el estado final + `_meta` con el resumen del budget.
    """
    tracker = BudgetTracker(budget=budget)
    state = initial_state(goal, mega_prompt, max_iterations=max_iterations)

    if no_web:
        from ai_agents.graphs import product_graph as pg
        original_web = pg.web_search
        pg.web_search = lambda *a, **k: {"available": False, "results": [], "sources": []}

    app = build_product_graph()
    config = {"recursion_limit": recursion_limit_for(max_iterations)}

    try:
        with budgeted_llm(tracker, llm_call=llm_call):
            result = app.invoke(state, config=config)
        result["status"] = result.get("status", "done") or "done"
    except BudgetExceeded:
        # Construir un resultado parcial con lo acumulado en state.
        result = dict(state)
        result["status"] = "budget_exceeded"
        result["final_report"] = result.get("final_report") or _budget_exceeded_report(tracker)
        logger.warning("[BudgetGuard] Run abortada: %s", tracker.to_dict())

    if no_web:
        pg.web_search = original_web  # type: ignore[possibly-undefined]

    result["_meta"] = {"budget": tracker.to_dict()}
    return result


def _budget_exceeded_report(tracker: BudgetTracker) -> str:
    return (
        "# ProductGraph — Presupuesto Excedido\n\n"
        f"- **Estado:** budget_exceeded\n"
        f"- **Tokens usados:** {tracker.used} / {tracker.budget}\n"
        f"- **Llamadas LLM:** {tracker.call_count}\n\n"
        "> La run se abortó por superar el budget de coste. "
        "Aumenta el budget o reduce max_iterations."
    )
