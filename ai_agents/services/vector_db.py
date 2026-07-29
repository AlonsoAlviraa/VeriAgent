"""
[AGENT-002 / AIQ-03] Chroma vector DB with tenant namespaces.
Falls back to in-memory namespace store when Chroma is unavailable.
"""

from __future__ import annotations

from typing import Dict, List, Optional

try:
    import chromadb
    from chromadb.config import Settings

    _HAS_CHROMA = True
except Exception:
    _HAS_CHROMA = False

try:
    from ai_agents.config import config

    _DEFAULT_PATH = getattr(config, "VECTOR_DB_PATH", "./data/chroma")
except Exception:
    _DEFAULT_PATH = "./data/chroma"

# Process-local fallback store: tenant_id -> {ids, documents, metadatas}
_MEMORY_NS: Dict[str, dict] = {}


class VectorDBService:
    def __init__(self, tenant_id: str = "default", path: Optional[str] = None):
        self.tenant_id = tenant_id
        self.collection_name = f"regulations_{tenant_id}"
        self.path = path or _DEFAULT_PATH
        self._client = None
        self._collection = None
        if _HAS_CHROMA:
            try:
                self._client = chromadb.PersistentClient(path=self.path)
                self._collection = self._client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine", "tenant_id": tenant_id},
                )
            except Exception:
                self._collection = None
        if self.tenant_id not in _MEMORY_NS:
            _MEMORY_NS[self.tenant_id] = {
                "ids": [],
                "documents": [],
                "metadatas": [],
            }

    def _memory(self) -> dict:
        """Garantiza y devuelve el bucket in-memory del tenant (robusto ante clears)."""
        bucket = _MEMORY_NS.get(self.tenant_id)
        if bucket is None:
            bucket = {"ids": [], "documents": [], "metadatas": []}
            _MEMORY_NS[self.tenant_id] = bucket
        return bucket

    def add_documents(self, documents: list, ids: list, metadatas: list):
        if self._collection is not None:
            self._collection.add(documents=documents, ids=ids, metadatas=metadatas)
        mem = self._memory()
        for i, doc, meta in zip(ids, documents, metadatas):
            if i in mem["ids"]:
                idx = mem["ids"].index(i)
                mem["documents"][idx] = doc
                mem["metadatas"][idx] = meta
            else:
                mem["ids"].append(i)
                mem["documents"].append(doc)
                mem["metadatas"].append(meta)

    def count(self) -> int:
        if self._collection is not None:
            try:
                return self._collection.count()
            except Exception:
                pass
        return len(self._memory()["ids"])

    def query(self, query_text: str, n_results: int = 3):
        if self._collection is not None and self.count() > 0:
            try:
                return self._collection.query(
                    query_texts=[query_text], n_results=n_results
                )
            except Exception:
                pass
        # Keyword fallback (tenant-scoped memory)
        mem = self._memory()
        q = query_text.lower()
        scored = []
        for doc, mid, meta in zip(mem["documents"], mem["ids"], mem["metadatas"]):
            score = sum(1 for t in q.split() if t in doc.lower())
            if score:
                scored.append((score, doc, mid, meta))
        scored.sort(key=lambda x: -x[0])
        top = scored[:n_results]
        return {
            "documents": [[t[1] for t in top]],
            "ids": [[t[2] for t in top]],
            "metadatas": [[t[3] for t in top]],
        }

    @staticmethod
    def clear_memory_namespace(tenant_id: str) -> None:
        _MEMORY_NS.pop(tenant_id, None)
