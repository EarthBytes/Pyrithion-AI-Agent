"""Sync documents from Google Drive into Qdrant for Q&A."""

from __future__ import annotations

import io
import logging
import tempfile
import uuid
from pathlib import Path

from app.config import settings
from app.memory.qdrant_client import QdrantMemoryClient
from app.memory.schemas import Document
from app.tools.documents import extract_text
from app.tools.rag import RAGTool
from app.tools.spreadsheets import chunk_text, format_spreadsheet_text

logger = logging.getLogger("app")

TEXT_MIME_TYPES = {
    "text/plain",
    "text/markdown",
    "text/csv",
    "application/json",
}
EXPORT_MIME = {
    "application/vnd.google-apps.document": "text/plain",
    "application/vnd.google-apps.spreadsheet": "text/csv",
    "application/vnd.google-apps.presentation": "text/plain",
}
SUPPORTED_EXTENSIONS = {".txt", ".md", ".csv", ".json", ".pdf", ".docx"}
DRIVE_ID_NAMESPACE = uuid.UUID("a3f7c2e1-9b4d-4f6a-8c1d-2e5f9a7b3c4d")


def drive_point_id(file_id: str) -> str:
    """Qdrant requires UUID or integer IDs; derive a stable UUID from Drive file id."""
    return str(uuid.uuid5(DRIVE_ID_NAMESPACE, file_id))


def _drive_service():
    if not settings.drive_configured:
        raise RuntimeError(
            "Google Drive is not configured. Set GOOGLE_DRIVE_FOLDER_ID and "
            "GOOGLE_SERVICE_ACCOUNT_FILE in .env"
        )
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise ImportError(
            "Install Google Drive dependencies: pip install google-api-python-client google-auth"
        ) from exc

    creds = service_account.Credentials.from_service_account_file(
        settings.google_service_account_file,
        scopes=["https://www.googleapis.com/auth/drive.readonly"],
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def _download_bytes(service, file_id: str, *, export_mime: str | None = None) -> bytes:
    from googleapiclient.http import MediaIoBaseDownload

    if export_mime:
        request = service.files().export_media(fileId=file_id, mimeType=export_mime)
    else:
        request = service.files().get_media(fileId=file_id)

    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return buffer.getvalue()


def list_drive_files() -> list[dict]:
    service = _drive_service()
    query = f"'{settings.google_drive_folder_id}' in parents and trashed = false"
    files: list[dict] = []
    page_token = None
    while True:
        response = (
            service.files()
            .list(
                q=query,
                fields="nextPageToken, files(id, name, mimeType)",
                pageToken=page_token,
            )
            .execute()
        )
        files.extend(response.get("files", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break
    return files


def _download_file_content(service, file_meta: dict) -> tuple[str, dict]:
    file_id = file_meta["id"]
    name = file_meta["name"]
    mime = file_meta.get("mimeType", "")

    metadata = {
        "source": "google_drive",
        "file_id": file_id,
        "filename": name,
        "mime_type": mime,
    }

    if mime in EXPORT_MIME:
        raw = _download_bytes(service, file_id, export_mime=EXPORT_MIME[mime])
        return raw.decode("utf-8", errors="ignore"), metadata

    if mime in TEXT_MIME_TYPES or Path(name).suffix.lower() in SUPPORTED_EXTENSIONS:
        raw = _download_bytes(service, file_id)
        suffix = Path(name).suffix.lower()
        if suffix in {".txt", ".md", ".csv", ".json"} or mime in TEXT_MIME_TYPES:
            return raw.decode("utf-8", errors="ignore"), metadata

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(raw)
            tmp_path = Path(tmp.name)
        try:
            return extract_text(tmp_path), metadata
        finally:
            tmp_path.unlink(missing_ok=True)

    raise ValueError(f"Unsupported file: {name} ({mime})")


def _is_spreadsheet(metadata: dict) -> bool:
    mime = metadata.get("mime_type", "")
    filename = metadata.get("filename", "")
    return "spreadsheet" in mime or filename.lower().endswith(".csv")


def _prepare_indexed_chunks(
    file_id: str, text: str, metadata: dict
) -> list[tuple[str, str, dict]]:
    filename = metadata["filename"]
    body = format_spreadsheet_text(text, filename) if _is_spreadsheet(metadata) else text
    full_text = f"Source file: {filename}\n\n{body}"
    chunks = chunk_text(full_text, chunk_size=6000)
    indexed: list[tuple[str, str, dict]] = []

    for index, chunk in enumerate(chunks):
        chunk_metadata = dict(metadata)
        if len(chunks) > 1:
            chunk_metadata["chunk"] = index + 1
            chunk_metadata["chunk_total"] = len(chunks)
        point_key = f"{file_id}-{index}" if len(chunks) > 1 else file_id
        indexed.append((drive_point_id(point_key), chunk, chunk_metadata))

    return indexed


def sync_drive_documents() -> int:
    """Download Drive files and upsert them into Qdrant. Returns document count."""
    if not settings.drive_configured:
        logger.info("Google Drive sync skipped (not configured)")
        return 0

    service = _drive_service()
    qdrant = QdrantMemoryClient()
    rag = RAGTool(qdrant_client=qdrant)

    files = list_drive_files()
    documents: list[Document] = []
    vectors: list[list[float]] = []

    for file_meta in files:
        try:
            text, metadata = _download_file_content(service, file_meta)
        except Exception as exc:
            logger.warning("Skipping Drive file %s: %s", file_meta.get("name"), exc)
            continue

        text = text.strip()
        if not text:
            continue

        for point_id, indexed_text, chunk_metadata in _prepare_indexed_chunks(
            file_meta["id"], text, metadata
        ):
            documents.append(
                Document(
                    id=point_id,
                    text=indexed_text,
                    metadata=chunk_metadata,
                )
            )
            vectors.append(rag.embed_fn(indexed_text))

    if not documents:
        logger.info("No documents found in Google Drive folder")
        return 0

    qdrant.upsert_documents(documents, vectors)
    logger.info("Synced %s documents from Google Drive", len(documents))
    return len(documents)
