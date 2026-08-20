"""Sync documents from Google Drive into Qdrant."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.tools.google_drive import sync_drive_documents


def main() -> None:
    count = sync_drive_documents()
    print(f"Synced {count} documents from Google Drive.")


if __name__ == "__main__":
    main()
