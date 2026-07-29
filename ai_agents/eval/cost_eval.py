"""
[AGENT-012 / Sprint 10] Cost evaluation harness for the zero-cost router.

Verifica que la estrategia multi-proveedor mantiene coste $0.00 incluso bajo
carga simulada. Modela el coste por proveedor y token, y valida que todos los
proveedores activos son de capa gratuita (coste unitario 0).

Diseño sin dependencias: no requiere litellm instalado. Modela los proveedores
del router y su coste unitario; un mock de ejecución simula N llamadas.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


# Coste por 1K tokens por proveedor. La filosofía del repo es FREE TIER = 0.
PROVIDER_UNIT_COST: Dict[str, float] = {
    "groq": 0.0,        # Llama 3.3 70B free tier
    "cerebras": 0.0,    # free tier
    "gemini": 0.0,      # Gemini Flash free tier
    "openrouter": 0.0,  # modelos :free
    "openai": 0.00015,  # fallback de pago (gpt-4o-mini ~$0.15/1M input)
}


@dataclass
class CallSimulation:
    """Una llamada LLM simulada."""
    provider: str
    tokens: int


@dataclass
class CostReport:
    total_calls: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    by_provider: Dict[str, Dict[str, float]] = field(default_factory=dict)
    free_tier_only: bool = True

    def summary(self) -> str:
        lines = [
            "=== Zero-Cost Router Eval ===",
            f"Total calls: {self.total_calls}",
            f"Total tokens: {self.total_tokens:,}",
            f"Total cost: ${self.cost_usd:.4f}",
            f"Free-tier only: {self.free_tier_only}",
            "By provider:",
        ]
        for p, stats in self.by_provider.items():
            lines.append(
                f"  - {p}: {int(stats['calls'])} calls, "
                f"{int(stats['tokens']):,} tokens, ${stats['cost']:.4f}"
            )
        return "\n".join(lines)


def evaluate_router_cost(
    calls: List[CallSimulation],
) -> CostReport:
    """
    Calcula el coste agregado de una secuencia de llamadas al router.

    Returns:
        CostReport con el coste total y desglose por proveedor.
    """
    report = CostReport()
    agg: Dict[str, Dict[str, float]] = {}

    for call in calls:
        provider = call.provider.lower()
        unit = PROVIDER_UNIT_COST.get(provider, 0.0)
        cost = (call.tokens / 1000.0) * unit

        report.total_calls += 1
        report.total_tokens += call.tokens
        report.cost_usd += cost
        if unit > 0:
            report.free_tier_only = False

        bucket = agg.setdefault(provider, {"calls": 0, "tokens": 0, "cost": 0.0})
        bucket["calls"] += 1
        bucket["tokens"] += call.tokens
        bucket["cost"] += cost

    report.by_provider = agg
    # Redondear para evitar ruido de coma flotante.
    report.cost_usd = round(report.cost_usd, 6)
    return report


def simulate_round_robin(
    providers: List[str],
    total_calls: int,
    avg_tokens_per_call: int = 500,
) -> List[CallSimulation]:
    """Genera una secuencia round-robin de llamadas (como el router real)."""
    if not providers:
        return []
    return [
        CallSimulation(provider=providers[i % len(providers)], tokens=avg_tokens_per_call)
        for i in range(total_calls)
    ]


# Proveedores gratuitos del repo (excluyendo openai que es fallback de pago).
FREE_PROVIDERS = ["groq", "cerebras", "gemini", "openrouter"]
