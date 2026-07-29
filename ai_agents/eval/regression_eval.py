"""
[AGENT-021 / Sprint 7-V2] Golden dataset + eval de regresión de specs de producto.

Compara specs generadas por el grafo contra referencias golden y detecta
degradación respecto a un baseline de scores.

Métricas (sin deps de ML pesadas, solo stdlib):
- **Cobertura de keywords**: % de términos clave del golden presentes en la spec.
- **Similitud léxica (Jaccard sobre tokens)**: solapamiento de vocabulario.
- **Score delta**: diferencia entre el quality_score de la run y el baseline.

Un caso "pasa" si cobertura ≥ umbral Y score delta dentro de tolerancia.

Uso:
    from ai_agents.eval.regression_eval import (
        GOLDEN_SPECS, evaluate_regression, DegradationMonitor
    )
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass, field
from statistics import mean
from typing import Any, Dict, List, Optional


# ============================================================
# GOLDEN DATASET
# ============================================================

@dataclass
class GoldenSpec:
    """Spec de referencia con score esperado y keywords críticas."""
    id: str
    goal: str
    # Campos esperados en la salida del grafo.
    expected_keywords: List[str]
    expected_score_min: float = 7.0
    # Texto de referencia (opcional, para similitud léxica).
    reference_text: str = ""


# Dataset golden de referencia. Cubre 5 dominios para evaluar generalización.
GOLDEN_SPECS: List[GoldenSpec] = [
    GoldenSpec(
        id="saas-productivity",
        goal="SaaS de productividad para equipos remotos",
        expected_keywords=["PRD", "arquitectura", "metricas", "fases", "pricing"],
        expected_score_min=7.0,
        reference_text=(
            "PRD con MVP definido. Arquitectura basada en microservicios. "
            "GTM con segmentacion y pricing por usuario. Metricas de activacion."
        ),
    ),
    GoldenSpec(
        id="fintech-compliance",
        goal="Herramienta de cumplimiento fiscal para autónomos",
        expected_keywords=["fiscal", "compliance", "factura", "IVA", "automatizacion"],
        expected_score_min=7.5,
        reference_text=(
            "Automatizacion de declaraciones fiscales. Compliance con normativa. "
            "Gestion de facturas e IVA. Arquitectura con cifrado."
        ),
    ),
    GoldenSpec(
        id="health-platform",
        goal="Plataforma de telemedicina para clínicas",
        expected_keywords=["privacidad", "GDPR", "citas", "historial", "video"],
        expected_score_min=7.0,
        reference_text=(
            "Citas online con video. Historial clinico con privacidad GDPR. "
            "Arquitectura HIPAA-ready. GTM orientado a clinicas."
        ),
    ),
    GoldenSpec(
        id="edtech-mobile",
        goal="App móvil de aprendizaje de idiomas gamificada",
        expected_keywords=["gamificacion", "retencion", "lecciones", "progreso", "metricas"],
        expected_score_min=6.5,
        reference_text=(
            "Lecciones cortas gamificadas. Sistema de progreso y retencion. "
            "Metricas de engagement. Monetizacion freemium."
        ),
    ),
    GoldenSpec(
        id="marketplace-b2b",
        goal="Marketplace B2B de proveedores industriales",
        expected_keywords=["catalogo", "RFQ", "verificacion", "pagos", "escrow"],
        expected_score_min=7.0,
        reference_text=(
            "Catalogo de proveedores verificados. Sistema de RFQ. Pagos con escrow. "
            "Arquitectura multi-tenant. GTM sector industrial."
        ),
    ),
]


# ============================================================
# REGRESSION EVALUATION
# ============================================================

# Stopwords mínimas para la similitud léxica.
_STOPWORDS = frozenset(
    "el la los las de del a al en y o un una unos unas por para con que es son "
    "se su sus lo le al mas mas menos muy".split()
)


@dataclass
class RegressionResult:
    """Resultado de evaluar una spec contra su golden."""
    golden_id: str
    keyword_coverage: float       # 0.0 - 1.0
    lexical_similarity: float     # 0.0 - 1.0 (Jaccard)
    score_delta: float            # actual - expected_min
    passed: bool
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _tokenize(text: str) -> set:
    """Tokeniza normalizando a lowercase y quitando stopwords."""
    tokens = re.findall(r"[a-záéíóúñ]{3,}", (text or "").lower())
    return {t for t in tokens if t not in _STOPWORDS}


def _jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def evaluate_against_golden(
    golden: GoldenSpec,
    *,
    generated_text: str = "",
    quality_score: float = 0.0,
    keyword_coverage_threshold: float = 0.6,
    score_delta_tolerance: float = -1.5,
) -> RegressionResult:
    """
    Evalúa una salida generada contra un golden.

    Args:
        generated_text: el reporte/PRD generado por el grafo.
        quality_score: score del critic para esta run.
        keyword_coverage_threshold: mínima cobertura de keywords para pasar.
        score_delta_tolerance: delta mínimo permitido (actual - expected_min).
            Negativo = se permite puntuar algo menos que el expected.
    """
    text = (generated_text or "").lower()
    # Cobertura de keywords (case-insensitive).
    found = sum(1 for kw in golden.expected_keywords if kw.lower() in text)
    coverage = found / max(1, len(golden.expected_keywords))

    # Similitud léxica contra el reference_text.
    sim = _jaccard(_tokenize(text), _tokenize(golden.reference_text)) if golden.reference_text else 0.0

    delta = quality_score - golden.expected_score_min
    passed = (
        coverage >= keyword_coverage_threshold
        and delta >= score_delta_tolerance
    )

    return RegressionResult(
        golden_id=golden.id,
        keyword_coverage=round(coverage, 3),
        lexical_similarity=round(sim, 3),
        score_delta=round(delta, 3),
        passed=passed,
        details={
            "expected_score_min": golden.expected_score_min,
            "actual_score": quality_score,
            "found_keywords": found,
            "total_keywords": len(golden.expected_keywords),
        },
    )


def evaluate_regression(
    runs: List[Dict[str, Any]],
    *,
    golden_specs: Optional[List[GoldenSpec]] = None,
    **thresholds,
) -> Dict[str, Any]:
    """
    Evalúa un conjunto de runs contra el golden dataset.

    Args:
        runs: lista de {golden_id, final_report/generated_text, quality_score}.
        golden_specs: dataset golden (default: GOLDEN_SPECS).

    Returns:
        {
          "results": [RegressionResult...],
          "pass_rate": float,
          "mean_coverage": float,
          "regression_detected": bool,
        }
    """
    goldens = golden_specs or GOLDEN_SPECS
    by_id = {g.id: g for g in goldens}

    results: List[RegressionResult] = []
    for run in runs:
        gid = run.get("golden_id")
        golden = by_id.get(gid)
        if golden is None:
            continue
        results.append(evaluate_against_golden(
            golden,
            generated_text=run.get("final_report") or run.get("generated_text", ""),
            quality_score=run.get("quality_score", 0.0),
            **thresholds,
        ))

    pass_rate = sum(1 for r in results if r.passed) / max(1, len(results))
    mean_coverage = mean(r.keyword_coverage for r in results) if results else 0.0

    return {
        "results": [r.to_dict() for r in results],
        "pass_rate": round(pass_rate, 3),
        "mean_coverage": round(mean_coverage, 3),
        "evaluated": len(results),
        "regression_detected": pass_rate < 0.7,
    }


# ============================================================
# DEGRADATION MONITOR
# ============================================================

class DegradationMonitor:
    """
    Detecta degradación comparando scores recientes contra un baseline.

    Persiste el baseline en disco para comparar entre runs/días.
    """

    def __init__(self, path: Optional[str] = None):
        self.path = path or os.path.join("data", "graph_eval", "baseline.json")

    def save_baseline(self, scores: List[float]) -> None:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        baseline = mean(scores) if scores else 0.0
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump({"baseline_mean": baseline, "n": len(scores)}, f)

    def load_baseline(self) -> Optional[float]:
        if not os.path.exists(self.path):
            return None
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f).get("baseline_mean")
        except Exception:
            return None

    def check(self, recent_scores: List[float], tolerance: float = 1.0) -> Dict[str, Any]:
        """
        Compara scores recientes contra el baseline.

        Returns:
            {"degraded": bool, "recent_mean": float, "baseline_mean": float, "delta": float}
        """
        baseline = self.load_baseline()
        recent_mean = mean(recent_scores) if recent_scores else 0.0
        if baseline is None:
            return {"degraded": False, "recent_mean": round(recent_mean, 2),
                    "baseline_mean": None, "delta": None}
        delta = round(recent_mean - baseline, 2)
        return {
            "degraded": delta < -tolerance,
            "recent_mean": round(recent_mean, 2),
            "baseline_mean": round(baseline, 2),
            "delta": delta,
        }
