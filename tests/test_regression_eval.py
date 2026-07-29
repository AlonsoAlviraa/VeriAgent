"""
Tests para regression_eval + degradation monitor (Sprint 7-V2).
"""

import pytest

from ai_agents.eval.regression_eval import (
    GOLDEN_SPECS,
    DegradationMonitor,
    GoldenSpec,
    evaluate_against_golden,
    evaluate_regression,
    _jaccard,
    _tokenize,
)


class TestGoldenDataset:
    def test_has_five_specs(self):
        assert len(GOLDEN_SPECS) >= 5

    def test_specs_have_keywords(self):
        for spec in GOLDEN_SPECS:
            assert spec.expected_keywords, f"{spec.id} sin keywords"
            assert len(spec.id) > 0
            assert spec.expected_score_min > 0


class TestJaccardAndTokenize:
    def test_jaccard_identical(self):
        assert _jaccard({"a", "b"}, {"a", "b"}) == 1.0

    def test_jaccard_disjoint(self):
        assert _jaccard({"a"}, {"b"}) == 0.0

    def test_jaccard_partial(self):
        assert 0 < _jaccard({"a", "b"}, {"b", "c"}) < 1

    def test_tokenize_lowercase_and_strips_stopwords(self):
        toks = _tokenize("El producto es muy bueno y factible")
        assert "producto" in toks
        assert "factible" in toks
        # Stopwords fuera.
        assert "el" not in toks and "muy" not in toks


class TestEvaluateAgainstGolden:
    def test_pass_when_keywords_and_score_ok(self):
        golden = GoldenSpec(
            id="t1", goal="g",
            expected_keywords=["PRD", "arquitectura", "metricas"],
            expected_score_min=7.0,
            reference_text="PRD arquitectura metricas",
        )
        result = evaluate_against_golden(
            golden,
            generated_text="El PRD define la arquitectura con metricas claras.",
            quality_score=8.0,
        )
        assert result.passed is True
        assert result.keyword_coverage == 1.0
        assert result.score_delta == pytest.approx(1.0)

    def test_fail_when_low_coverage(self):
        golden = GoldenSpec(
            id="t2", goal="g",
            expected_keywords=["PRD", "arquitectura", "metricas", "pricing"],
            expected_score_min=7.0,
        )
        result = evaluate_against_golden(
            golden, generated_text="solo menciona PRD", quality_score=9.0,
        )
        assert result.passed is False
        assert result.keyword_coverage < 0.6

    def test_fail_when_score_too_low(self):
        golden = GoldenSpec(
            id="t3", goal="g", expected_keywords=["x", "y"], expected_score_min=8.0,
        )
        result = evaluate_against_golden(
            golden, generated_text="x y", quality_score=2.0,
        )
        assert result.passed is False
        # delta = 2.0 - 8.0 = -6.0 < tolerance -1.5
        assert result.score_delta < -1.5

    def test_lexical_similarity_with_reference(self):
        golden = GoldenSpec(
            id="t4", goal="g", expected_keywords=["prd"],
            reference_text="prd arquitectura metricas pricing",
        )
        result = evaluate_against_golden(
            golden, generated_text="prd arquitectura metricas pricing fases",
        )
        assert result.lexical_similarity > 0.5


class TestEvaluateRegression:
    def test_full_pass_rate(self):
        runs = [
            {"golden_id": "saas-productivity", "generated_text": "PRD arquitectura metricas fases pricing", "quality_score": 8.0},
            {"golden_id": "fintech-compliance", "generated_text": "fiscal compliance factura IVA automatizacion", "quality_score": 8.0},
        ]
        report = evaluate_regression(runs)
        assert report["evaluated"] == 2
        assert report["pass_rate"] == 1.0
        assert report["regression_detected"] is False

    def test_regression_detected_when_low_pass_rate(self):
        runs = [
            {"golden_id": "saas-productivity", "generated_text": "nada relevante", "quality_score": 3.0},
            {"golden_id": "fintech-compliance", "generated_text": "tampoco", "quality_score": 3.0},
        ]
        report = evaluate_regression(runs)
        assert report["pass_rate"] < 0.7
        assert report["regression_detected"] is True

    def test_unknown_golden_id_skipped(self):
        runs = [{"golden_id": "no-existe", "generated_text": "x", "quality_score": 9.0}]
        report = evaluate_regression(runs)
        assert report["evaluated"] == 0

    def test_mean_coverage_computed(self):
        runs = [
            {"golden_id": "saas-productivity", "generated_text": "PRD arquitectura metricas fases pricing", "quality_score": 8.0},
        ]
        report = evaluate_regression(runs)
        assert report["mean_coverage"] == 1.0


class TestDegradationMonitor:
    def test_save_and_load_baseline(self, tmp_path):
        mon = DegradationMonitor(path=str(tmp_path / "baseline.json"))
        mon.save_baseline([8.0, 9.0, 7.5])
        loaded = mon.load_baseline()
        assert loaded is not None
        assert 7.0 < loaded < 9.0

    def test_load_nonexistent_returns_none(self, tmp_path):
        mon = DegradationMonitor(path=str(tmp_path / "nope.json"))
        assert mon.load_baseline() is None

    def test_check_detects_degradation(self, tmp_path):
        mon = DegradationMonitor(path=str(tmp_path / "b.json"))
        mon.save_baseline([9.0, 9.0])  # baseline ~9.0
        result = mon.check([5.0, 5.0], tolerance=1.0)  # recent ~5.0
        assert result["degraded"] is True
        assert result["delta"] < -1.0

    def test_check_no_degradation(self, tmp_path):
        mon = DegradationMonitor(path=str(tmp_path / "b.json"))
        mon.save_baseline([8.0, 8.0])
        result = mon.check([8.0, 7.5], tolerance=1.0)
        assert result["degraded"] is False

    def test_check_without_baseline(self, tmp_path):
        mon = DegradationMonitor(path=str(tmp_path / "none.json"))
        result = mon.check([8.0])
        assert result["degraded"] is False
        assert result["baseline_mean"] is None
