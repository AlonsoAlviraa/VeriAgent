"""
[AIQ-05] Tenant-aware regulation search with citations and empty-corpus guardrail.
"""

from __future__ import annotations

from typing import Type

from pydantic import BaseModel, Field

try:
    from crewai_tools import BaseTool
except Exception:  # lightweight fallback when crewai not installed
    class BaseTool:  # type: ignore
        name: str = ""
        description: str = ""

        def _run(self, *a, **k):
            raise NotImplementedError


from ai_agents.normative.corpus import NormativeCorpus
from ai_agents.services.vector_db import VectorDBService


class SearchInput(BaseModel):
    query: str = Field(..., description="Regulation concept to search")
    tenant_id: str = Field(default="default", description="Tenant namespace")


class SearchRegulationTool(BaseTool):
    name: str = "search_regulations"
    description: str = (
        "Search fiscal regulations (VeriFactu / Facturae / AEAT) with citations. "
        "Fails closed on empty corpus for the tenant."
    )
    args_schema: Type[BaseModel] = SearchInput

    def _run(self, query: str, tenant_id: str = "default") -> str:
        return search_regulations(query, tenant_id=tenant_id)


def search_regulations(
    query: str, tenant_id: str = "default", *, auto_seed: bool = True
) -> str:
    """Shipped entrypoint used by agents and unit tests (no CrewAI required)."""
    vdb = VectorDBService(tenant_id=tenant_id)
    # When auto_seed is disabled, evaluate only process-local memory for empty check
    if not auto_seed:
        vdb._collection = None
    if vdb.count() == 0:
        if not auto_seed:
            return (
                "EMPTY_CORPUS: No regulations loaded for tenant; "
                "refuse to answer without sources."
            )
        # try auto-load seeds into this tenant once
        corpus = NormativeCorpus()
        n = corpus.load_seeds()
        if n == 0:
            return (
                "EMPTY_CORPUS: No regulations loaded for tenant; "
                "refuse to answer without sources."
            )
        payload = corpus.as_chroma_payload()
        metas = []
        for m in payload["metadatas"]:
            mm = dict(m)
            mm["tenant_id"] = tenant_id
            metas.append(mm)
        vdb.add_documents(payload["documents"], payload["ids"], metas)

    if vdb.count() == 0:
        return (
            "EMPTY_CORPUS: No regulations loaded for tenant; "
            "refuse to answer without sources."
        )

    results = vdb.query(query, n_results=2)
    docs = (results.get("documents") or [[]])[0]
    metas = (results.get("metadatas") or [[]])[0]
    ids = (results.get("ids") or [[]])[0]
    if not docs:
        return "No relevant regulations found (corpus non-empty but no match)."

    chunks = []
    for i, doc in enumerate(docs):
        meta = metas[i] if i < len(metas) else {}
        cid = ids[i] if i < len(ids) else "?"
        source = meta.get("source", "unknown")
        url = meta.get("url", "")
        cite = f"[cite:{cid} source={source}" + (f" url={url}" if url else "") + "]"
        chunks.append(f"{cite}\n{doc}")
    return "\n---\n".join(chunks)
