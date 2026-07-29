"""
Tests para ai_agents.eval.critic_eval (consistencia del critic).

Usa un mock determinista del LLM para que el score sea reproducible y poder
verificar la métrica de estabilidad sin coste ni red.
"""

import json

from ai_agents.eval.critic_eval import (
    CriticEvalCase,
    DEFAULT_CASES,
    MAX_ACCEPTABLE_STDEV,
    evaluate_critic_consistency,
)


def _stable_critic_llm(score):
    """Mock LLM que siempre devuelve el mismo score (crítico determinista)."""
    def _fake(messages, **kwargs):
        return json.dumps({
            "quality_score": score,
            "critique": "ok",
            "feedback": [],
            "weak_areas": [],
        })
    return _fake


def _noisy_critic_llm(scores_cycle):
    """Mock LLM que rota scores (crítico ruidoso) para simular inestabilidad."""
    state = {"i": 0}

    def _fake(messages, **kwargs):
        s = scores_cycle[state["i"] % len(scores_cycle)]
        state["i"] += 1
        return json.dumps({
            "quality_score": s, "critique": "", "feedback": [], "weak_areas": [],
        })
    return _fake


class TestCriticConsistency:
    def test_stable_critic_is_reported_stable(self):
        """Un crítico que siempre da el mismo score → stdev 0 → stable True."""
        report = evaluate_critic_consistency(
            DEFAULT_CASES, runs_per_case=3,
            llm_call=_stable_critic_llm(7.0),
        )
        assert report["stable"] is True
        assert report["global_stdev_mean"] == 0.0
        for case in report["cases"]:
            assert case["stdev"] == 0.0
            assert all(s == 7.0 for s in case["scores"])

    def test_noisy_critic_is_reported_unstable(self):
        """Un crítico que oscila → stdev alta → stable False."""
        report = evaluate_critic_consistency(
            [CriticEvalCase(name="noisy")],
            runs_per_case=3,
            llm_call=_noisy_critic_llm([2.0, 8.0, 5.0]),
        )
        assert report["stable"] is False
        assert report["global_stdev_mean"] > MAX_ACCEPTABLE_STDEV

    def test_score_band_assertion(self):
        """expected_score_band marca in_band correctamente."""
        case = CriticEvalCase(
            name="banded",
            state_overrides={"product_spec": "x"},
            expected_score_band=(6.0, 9.0),
        )
        report = evaluate_critic_consistency(
            [case], runs_per_case=2, llm_call=_stable_critic_llm(7.5),
        )
        assert report["cases"][0]["in_band"] is True

        report_out = evaluate_critic_consistency(
            [case], runs_per_case=2, llm_call=_stable_critic_llm(3.0),
        )
        assert report_out["cases"][0]["in_band"] is False

    def test_empty_spec_scores_lower_than_rich(self):
        """El caso vacío debe puntuar distinto al rico con un critic con sesgo."""
        # Mock que devuelve score según presencia de PRD (heurística simple).
        def biased(messages, **kwargs):
            user = messages[-1]["content"] if messages else ""
            score = 8.0 if "PRD:" in user and "PRD completo" in user else 2.0
            return json.dumps({
                "quality_score": score, "critique": "", "feedback": [], "weak_areas": [],
            })

        report = evaluate_critic_consistency(
            DEFAULT_CASES, runs_per_case=1, llm_call=biased,
        )
        by_name = {c["name"]: c["mean"] for c in report["cases"]}
        assert by_name["rich_spec"] > by_name["empty_spec"]
