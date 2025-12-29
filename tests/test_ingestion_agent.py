import sys
import os
import unittest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ai_agents.graphs.ingestion_graph import ingestion_app

class TestIngestionAgent(unittest.TestCase):
    def test_happy_path(self):
        input_data = {"input_text": "ESTO ES UNA FACTURA DE PRUEBA"}
        output = ingestion_app.invoke(input_data)
        
        self.assertIsNotNone(output.get("validated_invoice"))
        self.assertIsNone(output.get("error"))
        print("Ingestion Graph Success:", output["validated_invoice"].number)

    def test_failure_path(self):
        input_data = {"input_text": "ESTO ES UN DOCUMENTO CUALQUIERA"}
        output = ingestion_app.invoke(input_data)
        
        self.assertIsNotNone(output.get("error"))
        print("Ingestion Graph Handled Error:", output["error"])

if __name__ == '__main__':
    unittest.main()
