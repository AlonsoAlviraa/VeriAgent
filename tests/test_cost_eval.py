"""
Tests para el eval de coste del router zero-cost (AGENT-012 / Sprint 10).
"""

import pytest

from ai_agents.eval.cost_eval import (
    FREE_PROVIDERS,
    PROVIDER_UNIT_COST,
    CallSimulation,
    CostReport,
    evaluate_router_cost,
    simulate_round_robin,
)


class TestZeroCost:
    def test_free_providers_yield_zero_cost(self):
        calls = simulate_round_robin(FREE_PROVIDERS, total_calls=100, avg_tokens_per_call=1000)
        report = evaluate_router_cost(calls)
        assert report.cost_usd == 0.0
        assert report.free_tier_only is True
        assert report.total_calls == 100
        assert report.total_tokens == 100_000
        # Desglose por los 4 proveedores free.
        assert set(report.by_provider.keys()) == set(FREE_PROVIDERS)

    def test_paid_provider_increases_cost(self):
        calls = [CallSimulation(provider="openai", tokens=1_000_000)]
        report = evaluate_router_cost(calls)
        assert report.cost_usd > 0
        assert report.free_tier_only is False

    def test_mixed_free_and_paid(self):
        calls = [
            CallSimulation(provider="groq", tokens=10_000),    # free
            CallSimulation(provider="openai", tokens=100_000),  # paid
        ]
        report = evaluate_router_cost(calls)
        assert report.free_tier_only is False
        # El coste viene solo de openai.
        assert report.by_provider["groq"]["cost"] == 0.0
        assert report.by_provider["openai"]["cost"] > 0

    def test_unknown_provider_defaults_to_zero(self):
        report = evaluate_router_cost([CallSimulation(provider="mystery", tokens=500)])
        assert report.cost_usd == 0.0
        assert report.total_tokens == 500

    def test_round_robin_distributes_evenly(self):
        calls = simulate_round_robin(["groq", "cerebras"], total_calls=4)
        assert [c.provider for c in calls] == ["groq", "cerebras", "groq", "cerebras"]

    def test_empty_input(self):
        report = evaluate_router_cost([])
        assert report.total_calls == 0
        assert report.cost_usd == 0.0
        assert report.free_tier_only is True

    def test_all_configured_free_providers_have_zero_unit_cost(self):
        for p in FREE_PROVIDERS:
            assert PROVIDER_UNIT_COST.get(p) == 0.0

    def test_summary_is_readable(self):
        report = evaluate_router_cost(
            simulate_round_robin(FREE_PROVIDERS, total_calls=4)
        )
        s = report.summary()
        assert "Zero-Cost Router Eval" in s
        assert "Total cost" in s
        assert "$0.0000" in s

    def test_high_load_stays_zero_cost(self):
        """Bajo carga alta (1000 llamadas, 4 proveedores) el coste sigue $0."""
        calls = simulate_round_robin(FREE_PROVIDERS, total_calls=1000, avg_tokens_per_call=2000)
        report = evaluate_router_cost(calls)
        assert report.cost_usd == 0.0
        assert report.total_tokens == 2_000_000
