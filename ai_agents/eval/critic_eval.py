"""
[AIQ-07 / Sprint 3] Critic consistency eval harness.

Mide la estabilidad del nodo `critic` de ProductGraph: ¿el quality_score es
reproducible para un mismo input? Un critic inestable haría oscilar el loop de
auto-mejora. La métrica principal es la desviación típica del score entre runs.

Diseño zero-cost y sin red: el LLM se inyecta (por defecto el router real, o un
mock en tests). Mismos patrones que rag_eval.py.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from ai_agents.graphs.product_graph import ProductGraphState, critic_node, initial_state


@dataclass
class CriticEvalCase:
    """Un caso de evaluación: un estado fijo sobre el que correr el critic."""
    name: str
    state_overrides: Dict[str, Any] = field(default_factory=dict)
    expected_score_band: Optional[tuple] = None  # (min, max) opcional para asertar


def _build_state(case: CriticEvalCase) -> Dict[str, Any]:
    """Construye un estado válido con los overrides del caso."""
    base = initial_state("Eval goal", "Eval prompt")
    base.update(case.state_overrides)
    return base


def evaluate_critic_consistency(
    cases: List[CriticEvalCase],
    runs_per_case: int = 3,
    llm_call: Optional[Callable] = None,
) -> Dict[str, Any]:
    """
    Evalúa la consistencia del critic.

    Args:
        cases: casos de evaluación a correr.
        runs_per_case: cuántas veces correr el critic sobre cada caso.
        llm_call: inyección del LLM (por defecto parchea _chat_completion del
            módulo product_graph). En tests se pasa un mock determinista.

    Returns:
        {
          "cases": [{name, scores, mean, stdev, in_band}],
          "global_stdev_mean": float,
          "stable": bool,   # True si la stdev media < MAX_ACCEPTABLE_STDEV
        }
    """
    from unittest.mock import patch

    results: List[Dict[str, Any]] = []
    stdevs: List[float] = []

    for case in cases:
        state = _build_state(case)
        scores: List[float] = []
        with patch("ai_agents.graphs.product_graph._chat_completion", side_effect=llm_call) if llm_call else _no_patch():
            for _ in range(runs_per_case):
                out = critic_node(state)
                scores.append(float(out.get("quality_score", 0.0)))

        mean = statistics.mean(scores)
        stdev = statistics.pstdev(scores) if len(scores) > 1 else 0.0
        in_band = True
        if case.expected_score_band is not None:
            lo, hi = case.expected_score_band
            in_band = all(lo <= s <= hi for s in scores)

        results.append({
            "name": case.name,
            "scores": scores,
            "mean": round(mean, 3),
            "stdev": round(stdev, 3),
            "in_band": in_band,
        })
        stdevs.append(stdev)

    global_stdev_mean = round(statistics.mean(stdevs), 3) if stdevs else 0.0
    return {
        "cases": results,
        "global_stdev_mean": global_stdev_mean,
        "stable": global_stdev_mean <= MAX_ACCEPTABLE_STDEV,
    }


class _no_patch:
    """Context manager nulo para no parchear cuando no se inyecta LLM."""
    def __enter__(self):
        return None

    def __exit__(self, *a):
        return False


# Umbral de estabilidad: stdev media del score <= 0.5 (sobre escala 0-10).
MAX_ACCEPTABLE_STDEV = 0.5


# Casos por defecto: cubren espectro bajo/medio/alto de calidad.
DEFAULT_CASES: List[CriticEvalCase] = [
    CriticEvalCase(
        name="empty_spec",
        state_overrides={
            "research_synthesis": "",
            "product_ideas": [],
            "product_spec": "",
            "technical_architecture": "",
            "gtm_strategy": "",
        },
    ),
    CriticEvalCase(
        name="rich_spec",
        state_overrides={
            "research_synthesis": "Mercado creciente. 3 competidores claros.",
            "product_ideas": [
                {"name": "Producto A", "feasibility_1_10": 9, "differentiator": "patente"},
            ],
            "product_spec": "PRD completo con métricas y fases.",
            "technical_architecture": "Arquitectura con stack concreto.",
            "gtm_strategy": "GTM con segmentación y pricing.",
        },
    ),
]
