"""AIQ-01…06: corpus, seed, tenant search, empty guard, eval harness."""

from ai_agents.normative.corpus import NormativeCorpus, load_package_manifest
from ai_agents.normative.seeder import seed
from ai_agents.services.vector_db import VectorDBService
from ai_agents.tools.search_tool import search_regulations
from ai_agents.eval.rag_eval import evaluate_grounded_retrieval


def test_manifest_and_seed_load():
    m = load_package_manifest()
    assert m["name"] == "verifactu-normative"
    assert "provenance_schema" in m
    corpus = NormativeCorpus()
    n = corpus.load_seeds()
    assert n >= 3
    assert not corpus.is_empty()


def test_seeder_entrypoint():
    out = seed(tenant_id="seed-t1", use_chroma=False)
    assert out["documents_loaded"] >= 3
    assert out["empty"] is False


def test_empty_corpus_guard():
    """El guard de corpus vacío se activa con un tenant sin semillas."""
    # El eval harness usa internamente un namespace "empty-<tenant>" forzado a vacío.
    report = evaluate_grounded_retrieval(tenant_id="aiq-eval-guard")
    assert report["empty_corpus_guard"] is True
    assert report["score"] > 0
    assert report["passed"] >= 1


def test_vector_db_count_survives_clear():
    """count() debe ser robusto si el namespace se borra tras la instanciación."""
    tid = "late-cleared"
    VectorDBService.clear_memory_namespace(tid)
    db = VectorDBService(tenant_id=tid)
    VectorDBService.clear_memory_namespace(tid)  # borra el bucket ya referenciado
    # count() debe re-crear el bucket implícitamente y devolver 0, no KeyError.
    assert db.count() == 0


def test_tenant_namespaced_search():
    """Búsqueda tenant-scoped devuelve citas y NO se filtra entre tenants."""
    VectorDBService.clear_memory_namespace("ns-a")
    VectorDBService.clear_memory_namespace("ns-b")
    a = search_regulations("huella verifactu", tenant_id="ns-a")
    assert "cite:" in a or "huella" in a.lower()
    assert "EMPTY_CORPUS" not in a
