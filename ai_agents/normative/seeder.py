"""
[AIQ-04] Regulation corpus seeder CLI / compose bootstrap entrypoint.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ai_agents.normative.corpus import NormativeCorpus
from ai_agents.services.vector_db import VectorDBService


def seed(tenant_id: str = "default", use_chroma: bool = False) -> dict:
    corpus = NormativeCorpus()
    n = corpus.load_seeds()
    result = {
        "tenant_id": tenant_id,
        "documents_loaded": n,
        "empty": n == 0,
        "namespace": f"regulations_{tenant_id}",
    }
    if use_chroma and n > 0:
        try:
            vdb = VectorDBService(tenant_id=tenant_id)
            payload = corpus.as_chroma_payload()
            # namespace via metadata
            metas = []
            for m in payload["metadatas"]:
                mm = dict(m)
                mm["tenant_id"] = tenant_id
                metas.append(mm)
            vdb.add_documents(payload["documents"], payload["ids"], metas)
            result["chroma"] = "ok"
        except Exception as exc:
            result["chroma"] = f"skip:{exc}"
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description="Seed VeriFactu normative corpus")
    p.add_argument("--tenant", default="default")
    p.add_argument("--chroma", action="store_true")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)
    out = seed(tenant_id=args.tenant, use_chroma=args.chroma)
    if args.json:
        print(json.dumps(out))
    else:
        print(f"Seeded {out['documents_loaded']} docs for tenant={out['tenant_id']}")
    return 0 if not out["empty"] else 1


if __name__ == "__main__":
    sys.exit(main())
