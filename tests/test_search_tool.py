import sys
import os
import unittest
from unittest.mock import MagicMock, patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mocks
sys.modules['crewai_tools'] = MagicMock()
# Mock BaseTool again for inheritance
class MockBaseTool:
    pass
sys.modules['crewai_tools'].BaseTool = MockBaseTool

# Mock vector db service before importing search tool
sys.modules['ai_agents.services.vector_db'] = MagicMock()

from ai_agents.tools.search_tool import SearchRegulationTool

class TestSearchTool(unittest.TestCase):
    @patch('ai_agents.tools.search_tool.VectorDBService')
    def test_run_search(self, MockDBService):
        # Setup mock return
        mock_instance = MockDBService.return_value
        mock_instance.query.return_value = {
            'documents': [["Regulation 1: Must include QR", "Regulation 2: No modifications allowed"]]
        }
        
        tool = SearchRegulationTool()
        result = tool._run("requisitos QR")
        
        self.assertIn("Regulation 1", result)
        print("Search Tool Output:\n", result)

if __name__ == '__main__':
    unittest.main()
