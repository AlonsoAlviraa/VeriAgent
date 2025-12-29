from typing import Type
from crewai_tools import BaseTool
from pydantic import BaseModel, Field

# Import the Vector DB Service
from ai_agents.services.vector_db import VectorDBService

class SearchInput(BaseModel):
    query: str = Field(..., description="The concept or regulation to search for (e.g., 'limite pagos efectivo').")

class SearchRegulationTool(BaseTool):
    name: str = "search_regulations"
    description: str = (
        "Useful for searching specific fiscal regulations, limits, or requirements "
        "in the VeriFactu/Ley Crea y Crece knowledge base."
    )
    args_schema: Type[BaseModel] = SearchInput

    def _run(self, query: str) -> str:
        try:
            # Instantiate service (mocked in tests, real in prod)
            db_service = VectorDBService()
            
            # Query the DB
            results = db_service.query(query, n_results=2)
            
            # Format results
            if not results or not results['documents']:
                return "No relevant regulations found."
            
            # Flatten list of lists
            docs = results['documents'][0] 
            return "\n---\n".join(docs)
            
        except Exception as e:
            return f"Error searching regulations: {str(e)}"
