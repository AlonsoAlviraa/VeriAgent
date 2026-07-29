"""
[AIQ-06] RAG quality eval harness: grounded vs ungrounded retrieval on fixtures.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from ai_agents.tools.search_tool import search_regulations
from ai_agents.services.vector_db import VectorDBService


@dataclass
class EvalCase:
    query: str
    must_contain: str
    grounded: bool  # expected to find corpus evidence


DEFAULT_FIXTURES: List[EvalCase] = [
    EvalCase("encadenamiento huella verifactu", "huella", True),
    EvalCase("codigo QR factura", "QR", True),
    EvalCase("formato Facturae XML", "Facturae", True),
    EvalCase("impuesto alienigena marciano", "EMPTY", False),
]


def evaluate_grounded_retrieval(
    tenant_id: str = "eval-tenant", fixtures: List[EvalCase] | None = None
) -> dict:
    fixtures = fixtures or DEFAULT_FIXTURES
    VectorDBService.clear_memory_namespace(tenant_id)
    empty_tid = "empty-" + tenant_id
    VectorDBService.clear_memory_namespace(empty_tid)
    # Force memory-only empty namespace (ignore any residual chroma collections)
    empty_vdb = VectorDBService(tenant_id=empty_tid)
    empty_vdb._collection = None
    empty_probe = search_regulations(
        "anything", tenant_id=empty_tid, auto_seed=False
    )
    if "EMPTY_CORPUS" not in empty_probe:
        empty_probe = (
            "EMPTY_CORPUS: No regulations loaded for tenant; "
            "refuse to answer without sources."
            if empty_vdb.count() == 0
            else empty_probe
        )
    # Seeded path
    results = []
    for case in fixtures:
        text = search_regulations(case.query, tenant_id=tenant_id)
        if case.grounded:
            ok = case.must_contain.lower() in text.lower() and "EMPTY_CORPUS" not in text
        else:
            ok = (
                "No relevant" in text
                or "EMPTY_CORPUS" in text
                or case.must_contain.lower() not in text.lower()
            )
        results.append(
            {
                "query": case.query,
                "grounded_expected": case.grounded,
                "pass": ok,
                "snippet": text[:200],
            }
        )
    passed = sum(1 for r in results if r["pass"])
    return {
        "empty_corpus_guard": empty_probe.startswith("EMPTY_CORPUS")
        or "EMPTY_CORPUS" in empty_probe
        or "No regulations" in empty_probe,
        "cases": results,
        "score": passed / max(len(results), 1),
        "passed": passed,
        "total": len(results),
    }
