import re


def extract_filename_hint(text: str) -> str | None:
    """Pull a likely Drive filename from the user's question."""
    if not text:
        return None

    patterns = [
        r"(?:from|in|using|within)\s+['\"]?([a-zA-Z0-9_\-\s]+?)['\"]?\s+(?:sheet|spreadsheet|file|document)",
        r"(?:sheet|spreadsheet|file|document)\s+['\"]?([a-zA-Z0-9_\-\s]+?)['\"]?(?:\s|$|\.|,)",
        r"['\"]([a-zA-Z0-9_\-\s]+)['\"]",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            hint = re.sub(r"\s+", "_", match.group(1).strip().lower())
            hint = hint.replace(" ", "_")
            if len(hint) >= 3:
                return hint.replace("__", "_")

    for token in re.findall(r"[a-zA-Z][a-zA-Z0-9_\-]{2,}", text):
        if "_" in token and not token.lower().endswith("sheet"):
            return token.lower()
    return None
