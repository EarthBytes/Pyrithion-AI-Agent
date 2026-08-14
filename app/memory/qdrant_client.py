from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.config import settings
from app.memory.schemas import Document


class QdrantMemoryClient:
    def __init__(
        self,
        url: str | None = None,
        collection: str | None = None,
        api_key: str | None = None,
    ):
        self.url = url or settings.qdrant_url
        self.collection = collection or settings.qdrant_collection
        self.client = QdrantClient(url=self.url, api_key=api_key or settings.qdrant_api_key)

    def ensure_collection(self, vector_size: int = 384) -> None:
        if self.client.collection_exists(self.collection):
            return
        self.client.create_collection(
            collection_name=self.collection,
            vectors_config=qmodels.VectorParams(
                size=vector_size,
                distance=qmodels.Distance.COSINE,
            ),
        )

    def upsert_documents(self, documents: list[Document], vectors: list[list[float]]) -> None:
        if not documents:
            return
        self.ensure_collection(len(vectors[0]))
        points = [
            qmodels.PointStruct(
                id=doc.id,
                vector=vector,
                payload={"text": doc.text, **doc.metadata},
            )
            for doc, vector in zip(documents, vectors)
        ]
        self.client.upsert(collection_name=self.collection, points=points)

    def search(self, query_vector: list[float], limit: int = 5) -> list[Document]:
        if not self.client.collection_exists(self.collection):
            return []
        hits = self.client.search(
            collection_name=self.collection,
            query_vector=query_vector,
            limit=limit,
        )
        return [
            Document(
                id=str(hit.id),
                text=hit.payload.get("text", ""),
                metadata={k: v for k, v in hit.payload.items() if k != "text"},
                score=hit.score,
            )
            for hit in hits
        ]
