import hashlib
import logging
import math

import httpx

from app.config import settings
from app.memory.qdrant_client import QdrantMemoryClient

logger = logging.getLogger("app")


class RAGTool:
    """Retrieves relevant documents from Qdrant for context enrichment."""

    def __init__(
        self,
        qdrant_client: QdrantMemoryClient | None = None,
        embed_fn=None,
        limit: int = 5,
    ):
        self.qdrant = qdrant_client or QdrantMemoryClient()
        self.embed_fn = embed_fn or self._resolve_embedder()
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
        except Exception as exc:
            logger.warning("RAG search failed: %s", exc)
            return []

    def _resolve_embedder(self):
        provider = (settings.embedding_provider or "local").lower()

        if provider == "api":
            if not settings.llm_api_key:
                logger.warning("embedding_provider=api but LLM_API_KEY empty; using local")
                return self._default_embed
            logger.info("Using API embeddings (%s)", settings.embedding_model)
            return self._api_embed

        if provider in {"sentence-transformers", "st"}:
            try:
                from sentence_transformers import SentenceTransformer

                model = SentenceTransformer("all-MiniLM-L6-v2")
                dim = settings.embedding_dim

                def _st_embed(text: str) -> list[float]:
                    vector = model.encode(text, normalize_embeddings=True).tolist()
                    if len(vector) > dim:
                        return vector[:dim]
                    if len(vector) < dim:
                        return vector + [0.0] * (dim - len(vector))
                    return vector

                logger.info("Using sentence-transformers embeddings")
                return _st_embed
            except Exception as exc:
                logger.warning("sentence-transformers unavailable (%s); using local", exc)
                return self._default_embed

        logger.info("Using deterministic local embeddings")
        return self._default_embed

    def _api_embed(self, text: str) -> list[float]:
        headers = {
            "Authorization": f"Bearer {settings.llm_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": settings.embedding_model,
            "input": text,
        }
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                "https://openrouter.ai/api/v1/embeddings",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            vector = response.json()["data"][0]["embedding"]

        dim = settings.embedding_dim
        if len(vector) > dim:
            return vector[:dim]
        if len(vector) < dim:
            return vector + [0.0] * (dim - len(vector))
        return vector

    @staticmethod
    def _default_embed(text: str) -> list[float]:
        """Improved deterministic embedding via hashing trick (local fallback)."""
        size = settings.embedding_dim
        vector = [0.0] * size
        tokens = text.lower().split() or [text]
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
            idx = int(digest[:8], 16) % size
            sign = 1.0 if int(digest[8:10], 16) % 2 == 0 else -1.0
            vector[idx] += sign
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norm for v in vector]
