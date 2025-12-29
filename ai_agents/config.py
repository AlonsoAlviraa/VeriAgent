import os
from pydantic import BaseModel

class AIConfig(BaseModel):
    """
    [AGENT-001] Central configuration for AI Agents.
    """
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    VECTOR_DB_PATH: str = os.getenv("VECTOR_DB_PATH", "./chroma_db")
    MODEL_NAME: str = "gpt-4-turbo-preview"
    
    # Thresholds
    CONFIDENCE_THRESHOLD: float = 0.85

config = AIConfig()
