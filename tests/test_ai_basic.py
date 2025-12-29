import sys
import os
import unittest
from unittest.mock import MagicMock, patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock chromadb to avoid installation/runtime heavy deps in CI test
sys.modules['chromadb'] = MagicMock()
sys.modules['chromadb.config'] = MagicMock()

from ai_agents.config import config
from ai_agents.services.vector_db import VectorDBService

class TestAIFoundation(unittest.TestCase):
    def test_config(self):
        self.assertEqual(config.MODEL_NAME, "gpt-4-turbo-preview")
    
    def test_vectordb_init(self):
        db = VectorDBService()
        self.assertIsNotNone(db.client)
        print("VectorDB Service initialized successfully (Mocked)")

if __name__ == '__main__':
    unittest.main()
