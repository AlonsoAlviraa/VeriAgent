"""
[AGENT-018 / Sprint 3-V2] Critic con rúbrica multi-eje + memoria de aprendizaje.

Mejora el nodo `critic` con:
1. **Rúbrica multi-eje**: 4 scores separados (completitud, realismo, originalidad,
   accionabilidad, cada uno 0-10) + score global agregado. Mucho más informativo
   que el score único original.
2. **Memoria/learning entre runs**: store persistente de patrones de feedback
   recurrentes. El critic consulta feedback previo para no repetir los mismos
   errores y detectar degradación.

Compatibilidad: el nodo `critic_node` original de product_graph sigue funcionando;
este módulo expone `critique_with_rubric()` reutilizable y un `FeedbackMemory`
persistente a disco.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Directorio de memoria de feedback (persistente entre runs).
MEMORY_DIR = os.getenv("PRODUCT_GRAPH_MEMORY_DIR", "data/graph_memory")

# Pesos de los ejes para el score global (suman 1.0).
AXIS_WEIGHTS = {
    "completitud": 0.30,
    "realismo": 0.25,
    "originalidad": 0.20,
    "acionabilidad": 0.25,
}


# ============================================================
# RUBRIC CRITIQUE
# ============================================================

@dataclass
class RubricScore:
    """Score de un eje individual."""
    axis: str
    score: float          # 0.0 - 10.0
    justification: str = ""


@dataclass
class RubricCritique:
    """Resultado completo del critic con rúbrica."""
    axes: List[RubricScore] = field(default_factory=list)
    global_score: float = 0.0
    critique: str = ""
    feedback: List[str] = field(default_factory=list)
    weak_areas: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            "axes": [asdict(a) for a in self.axes],
        }


def critique_with_rubric(
    state: Dict[str, Any],
    *,
    llm_call=None,
    prior_feedback: Optional[List[str]] = None,
) -> RubricCritique:
    """
    Evalúa el estado del grafo con una rúbrica de 4 ejes.

    Args:
        state: estado del grafo (usa research_synthesis, product_ideas, spec, etc.).
        llm_call: LLM inyectado (mock en tests). Default: router real.
        prior_feedback: feedback recurrente de runs anteriores (de FeedbackMemory).

    Returns:
        RubricCritique con scores por eje + score global + feedback accionable.
    """
    llm = llm_call or _llm_call

    system = (
        "Eres un crítico implacable y justo. Evalúa la calidad de un producto "
        "propuesto en 4 ejes independientes (0-10 cada uno):\n"
        "- completitud: ¿cubre PRD + arquitectura + GTM con detalle suficiente?\n"
        "- realismo: ¿es técnicamente y comercialmente viable?\n"
        "- originalidad: ¿se diferencia de lo existente?\n"
        "- acionabilidad: ¿se puede ejecutar con fases/métricas concretas?\n"
        "Responde SOLO JSON: "
        '{"axes": [{"axis": str, "score": float, "justification": str}, ...], '
        '"critique": str, "feedback": [str], '
        '"weak_areas": [subset of "research","ideas","spec"]}.'
    )
    user = (
        f"OBJETIVO: {state.get('goal','')}\n\n"
        f"SÍNTESIS:\n{state.get('research_synthesis','')[:1500]}\n\n"
        f"IDEAS (top 3):\n{json.dumps(state.get('product_ideas',[])[:3], ensure_ascii=False)}\n\n"
        f"PRD:\n{state.get('product_spec','')[:2000]}\n\n"
        f"ARQUITECTURA:\n{state.get('technical_architecture','')[:1200]}\n\n"
        f"GTM:\n{state.get('gtm_strategy','')[:1200]}\n\n"
        f"FEEDBACK RECURRENTE A EVITAR:\n{json.dumps(prior_feedback or [], ensure_ascii=False)}\n\n"
        "Evalúa con la rúbrica."
    )
    raw = llm(system, user)
    parsed = _safe_json_obj(raw)
    return _build_critique(parsed)


def _build_critique(parsed: Dict[str, Any]) -> RubricCritique:
    """Construye RubricCritique desde el JSON parseado del LLM."""
    axes_raw = parsed.get("axes", [])
    axes: List[RubricScore] = []
    for a in axes_raw if isinstance(axes_raw, list) else []:
        if not isinstance(a, dict):
            continue
        try:
            axes.append(RubricScore(
                axis=str(a.get("axis", "")),
                score=max(0.0, min(10.0, float(a.get("score", 0)))),
                justification=str(a.get("justification", "")),
            ))
        except (TypeError, ValueError):
            continue

    # Garantizar los 4 ejes (rellenar con 0 si faltan).
    seen = {a.axis for a in axes}
    for required in AXIS_WEIGHTS:
        if required not in seen:
            axes.append(RubricScore(axis=required, score=0.0, justification="no evaluado"))

    global_score = _aggregate(axes)

    feedback = parsed.get("feedback", [])
    feedback = feedback if isinstance(feedback, list) else [str(feedback)]
    weak = parsed.get("weak_areas", [])
    weak = [w for w in (weak if isinstance(weak, list) else [str(weak)])
            if w in ("research", "ideas", "spec")]

    return RubricCritique(
        axes=axes,
        global_score=global_score,
        critique=str(parsed.get("critique", "") or ""),
        feedback=[str(f) for f in feedback],
        weak_areas=weak,
    )


def _aggregate(axes: List[RubricScore]) -> float:
    """Agrega los scores por eje usando AXIS_WEIGHTS."""
    by_axis = {a.axis: a.score for a in axes}
    total = 0.0
    for axis, weight in AXIS_WEIGHTS.items():
        total += by_axis.get(axis, 0.0) * weight
    return round(max(0.0, min(10.0, total)), 2)


# ============================================================
# FEEDBACK MEMORY (persistent learning across runs)
# ============================================================

class FeedbackMemory:
    """
    Memoria persistente de patrones de feedback entre runs.

    Almacena feedback recurrente en `data/graph_memory/feedback.json` para que
    el critic lo consulte en la siguiente run y detecte errores repetidos o
    degradación.
    """

    def __init__(self, path: Optional[str] = None):
        self.path = path or os.path.join(MEMORY_DIR, "feedback.json")

    def load(self) -> List[str]:
        if not os.path.exists(self.path):
            return []
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            items = data.get("items", [])
            return [i["feedback"] for i in items if isinstance(i, dict) and i.get("feedback")]
        except Exception:
            return []

    def record(self, critique: RubricCritique, *, thread_id: str = "") -> None:
        """Registra el feedback de una run en la memoria."""
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        data = {"items": []}
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {"items": []}
        for fb in critique.feedback:
            data["items"].append({
                "feedback": fb,
                "thread_id": thread_id,
                "score": critique.global_score,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        # Capping: keep last 100 items to avoid unbounded growth.
        data["items"] = data["items"][-100:]
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def recurring(self, top_n: int = 5) -> List[str]:
        """Devuelve el feedback más frecuente (heurística: últimas N entradas)."""
        all_items = self.load()
        # Heurística simple: contar ocurrencias de substrings cortos.
        from collections import Counter
        counts: Counter = Counter()
        for fb in all_items:
            key = fb[:60]  # normaliza por prefijo
            counts[key] += 1
        return [k for k, _ in counts.most_common(top_n)]

    def clear(self) -> None:
        if os.path.exists(self.path):
            os.remove(self.path)


# ============================================================
# Helpers
# ============================================================

def _llm_call(system: str, user: str) -> str:
    from ai_agents.graphs.product_graph import _llm
    return _llm(system, user, temperature=0.2)


def _safe_json_obj(raw: str) -> Dict[str, Any]:
    if not raw:
        return {}
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
    return {}
