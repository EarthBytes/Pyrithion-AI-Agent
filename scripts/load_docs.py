"""Load reference documents into Qdrant for Q&A."""

import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings
from app.memory.qdrant_client import QdrantMemoryClient
from app.memory.schemas import Document
from app.tools.google_drive import sync_drive_documents
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


def load_sample_docs() -> int:
    qdrant = QdrantMemoryClient()
    rag = RAGTool(qdrant_client=qdrant)

    documents = [
        Document(id=str(uuid.uuid4()), text=doc["text"], metadata=doc["metadata"])
        for doc in SAMPLE_DOCS
    ]
    vectors = [rag.embed_fn(doc.text) for doc in documents]
    qdrant.upsert_documents(documents, vectors)
    return len(documents)


def load_docs() -> int:
    if settings.google_drive_folder_id and settings.google_service_account_file:
        if settings.drive_configured:
            try:
                return sync_drive_documents()
            except Exception as exc:
                print(f"Google Drive sync failed: {exc}")
                print("Falling back to sample documents.")
        else:
            print(
                "Google Drive configured but credentials file not found: "
                f"{settings.google_service_account_file}\n"
                "Falling back to sample documents."
            )
    count = load_sample_docs()
    print(f"Loaded {count} sample documents into Qdrant collection '{settings.qdrant_collection}'.")
    return count


def main() -> None:
    load_docs()


if __name__ == "__main__":
    main()
