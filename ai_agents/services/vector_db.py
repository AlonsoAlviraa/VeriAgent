import chromadb
from chromadb.config import Settings
from ai_agents.config import config

class VectorDBService:
    """
    [AGENT-002] Manages interaction with ChromaDB for RAG (Regulations).
    """
    def __init__(self):
        self.client = chromadb.PersistentClient(path=config.VECTOR_DB_PATH)
        self.collection = self.client.get_or_create_collection(
            name="regulations",
            metadata={"hnsw:space": "cosine"}
        )

    def add_documents(self, documents: list[str], ids: list[str], metadatas: list[dict]):
        self.collection.add(
            documents=documents,
            ids=ids,
            metadatas=metadatas
        )

    def query(self, query_text: str, n_results: int = 3):
        return self.collection.query(
            query_texts=[query_text],
            n_results=n_results
        )
