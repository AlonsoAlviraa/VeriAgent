"""
Foundation tests for AI agents config and VectorDBService.

Actualizado al contrato real de VectorDBService (ai_agents/services/vector_db.py):
- El atributo interno es _client/_collection (no `client`).
- Hay fallback in-memory tenant-scoped cuando ChromaDB no está disponible.
- No se mockea chromadb a nivel módulo: el propio servicio degrada con try/except.
"""
import sys
import os
import unittest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ai_agents.config import config
from ai_agents.services.vector_db import VectorDBService


class TestAIFoundation(unittest.TestCase):
    def test_config(self):
        self.assertEqual(config.MODEL_NAME, "gpt-4-turbo-preview")

    def test_vectordb_init(self):
        """El servicio se inicializa y expone la colección/fallback in-memory."""
        db = VectorDBService(tenant_id="test-foundation")
        # El servicio siempre expone un estado usable (Chroma real o fallback memory).
        self.assertIsNotNone(db)
        self.assertEqual(db.tenant_id, "test-foundation")
        self.assertTrue(hasattr(db, "_client"))
        self.assertTrue(hasattr(db, "_collection"))
        # count() debe funcionar incluso sin Chroma (devuelve 0 al inicio).
        self.assertIsInstance(db.count(), int)

    def test_vectordb_memory_fallback_add_and_query(self):
        """Sin Chroma, el fallback in-memory soporta add/query/count."""
        tid = "memory-only-foundation"
        VectorDBService.clear_memory_namespace(tid)
        db = VectorDBService(tenant_id=tid)
        db._collection = None  # forzar path de fallback
        self.assertEqual(db.count(), 0)

        db.add_documents(
            documents=["Facturae es el formato de factura electrónica."],
            ids=["doc-1"],
            metadatas=[{"source": "test"}],
        )
        self.assertEqual(db.count(), 1)
        res = db.query("facturae", n_results=1)
        docs = (res.get("documents") or [[]])[0]
        self.assertEqual(len(docs), 1)
        self.assertIn("Facturae", docs[0])


if __name__ == '__main__':
    unittest.main()
