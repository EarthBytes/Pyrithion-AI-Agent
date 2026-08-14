from pathlib import Path

from app.config import settings
from app.memory.qdrant_client import QdrantMemoryClient


class RAGTool:
    """Retrieves relevant documents from Qdrant for context enrichment."""

    def __init__(
        self,
        qdrant_client: QdrantMemoryClient | None = None,
        embed_fn=None,
        limit: int = 5,
    ):
        self.qdrant = qdrant_client or QdrantMemoryClient()
        self.embed_fn = embed_fn or self._default_embed
        self.limit = limit

    def search(self, query: str) -> list[dict]:
        try:
            vector = self.embed_fn(query)
            docs = self.qdrant.search(vector, limit=self.limit)
            return [
                {
                    "text": doc.text,
                    "score": doc.score,
                    "metadata": doc.metadata,
                }
                for doc in docs
            ]
        except Exception:
            return []

    @staticmethod
    def _default_embed(text: str) -> list[float]:
        # Lightweight deterministic fallback when no embedder is configured.
        seed = sum(ord(c) for c in text) or 1
        size = 384
        return [((seed * (i + 1)) % 997) / 997.0 for i in range(size)]
