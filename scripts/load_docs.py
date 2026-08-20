"""Load sample reference documents into Qdrant for RAG enrichment."""

import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.memory.qdrant_client import QdrantMemoryClient
from app.memory.schemas import Document
from app.tools.rag import RAGTool

SAMPLE_DOCS = [
    {
        "text": (
            "Energy anomaly detection best practice: compare daily usage against "
            "a rolling 30-day baseline and flag spikes above 2 standard deviations."
        ),
        "metadata": {"source": "internal-playbook", "topic": "energy"},
    },
    {
        "text": (
            "Industry benchmark for commercial buildings: typical daily energy "
            "consumption ranges from 70-120 kWh depending on season and occupancy."
        ),
        "metadata": {"source": "industry-benchmark", "topic": "energy"},
    },
    {
        "text": (
            "Revenue trend analysis: use week-over-week and month-over-month "
            "comparisons; highlight regions with sustained decline over 4+ weeks."
        ),
        "metadata": {"source": "internal-playbook", "topic": "revenue"},
    },
    {
        "text": (
            "Churn analysis recommendation: segment users by plan and tenure; "
            "focus retention efforts on accounts showing declining engagement."
        ),
        "metadata": {"source": "internal-playbook", "topic": "churn"},
    },
]


def load_docs() -> None:
    qdrant = QdrantMemoryClient()
    rag = RAGTool(qdrant_client=qdrant)

    documents = [
        Document(id=str(uuid.uuid4()), text=doc["text"], metadata=doc["metadata"])
        for doc in SAMPLE_DOCS
    ]
    vectors = [rag.embed_fn(doc.text) for doc in documents]
    qdrant.upsert_documents(documents, vectors)
    print(f"Loaded {len(documents)} documents into Qdrant collection '{qdrant.collection}'.")


def main() -> None:
    load_docs()


if __name__ == "__main__":
    main()
