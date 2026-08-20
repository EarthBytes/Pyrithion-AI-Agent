import csv
from io import StringIO


def format_spreadsheet_text(csv_text: str, filename: str) -> str:
    """Turn raw CSV into readable row-by-row text for the LLM."""
    reader = csv.reader(StringIO(csv_text))
    rows = [row for row in reader if any(cell.strip() for cell in row)]
    if not rows:
        return csv_text

    headers = [cell.strip() for cell in rows[0]]
    lines = [
        f"Spreadsheet: {filename}",
        f"Columns: {', '.join(headers)}",
        "",
    ]
    for index, row in enumerate(rows[1:], start=1):
        pairs = []
        for header, value in zip(headers, row):
            value = value.strip()
            if value:
                pairs.append(f"{header}={value}")
        if pairs:
            lines.append(f"Row {index}: " + "; ".join(pairs))
    return "\n".join(lines)


def chunk_text(text: str, chunk_size: int = 6000) -> list[str]:
    if len(text) <= chunk_size:
        return [text]
    chunks: list[str] = []
    start = 0
    while start < len(text):
        chunks.append(text[start : start + chunk_size])
        start += chunk_size
    return chunks
