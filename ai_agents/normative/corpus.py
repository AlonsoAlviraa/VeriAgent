"""
[AIQ-01] Normative corpus package with provenance metadata.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

PACKAGE_ROOT = Path(__file__).resolve().parent
SEED_DIR = PACKAGE_ROOT / "seed"
MANIFEST_PATH = PACKAGE_ROOT / "manifest.json"


@dataclass
class CorpusDocument:
    id: str
    title: str
    text: str
    source: str
    provenance: Dict[str, str] = field(default_factory=dict)
    topics: List[str] = field(default_factory=list)

    def to_metadata(self) -> dict:
        return {
            "title": self.title,
            "source": self.source,
            "topics": ",".join(self.topics),
            **self.provenance,
        }


def load_package_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        return {
            "name": "verifactu-normative",
            "version": "0.1.0",
            "documents": 0,
            "empty": True,
            "provenance_schema": ["source", "retrieved_at", "license"],
        }
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


class NormativeCorpus:
    """In-memory + disk seed loader; empty-collection contract when no seeds."""

    def __init__(self, seed_dir: Optional[Path] = None):
        self.seed_dir = seed_dir or SEED_DIR
        self.documents: List[CorpusDocument] = []

    def is_empty(self) -> bool:
        return len(self.documents) == 0

    def load_seeds(self) -> int:
        self.documents.clear()
        if not self.seed_dir.exists():
            return 0
        for path in sorted(self.seed_dir.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            docs = data if isinstance(data, list) else data.get("documents", [data])
            for d in docs:
                self.documents.append(
                    CorpusDocument(
                        id=d["id"],
                        title=d.get("title", d["id"]),
                        text=d["text"],
                        source=d.get("source", path.name),
                        provenance=d.get("provenance", {}),
                        topics=d.get("topics", []),
                    )
                )
        return len(self.documents)

    def as_chroma_payload(self) -> dict:
        return {
            "documents": [d.text for d in self.documents],
            "ids": [d.id for d in self.documents],
            "metadatas": [d.to_metadata() for d in self.documents],
        }

    def keyword_search(self, query: str, n: int = 3) -> List[CorpusDocument]:
        q = query.lower()
        scored = []
        for d in self.documents:
            score = sum(1 for tok in q.split() if tok in d.text.lower() or tok in d.title.lower())
            if score:
                scored.append((score, d))
        scored.sort(key=lambda x: -x[0])
        return [d for _, d in scored[:n]]
