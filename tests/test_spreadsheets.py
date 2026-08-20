from app.tools.spreadsheets import chunk_text, format_spreadsheet_text


def test_format_spreadsheet_text():
    csv_text = "Category,Amount\nMarketing,6000\nSales,12000"
    formatted = format_spreadsheet_text(csv_text, "budget.csv")
    assert "Spreadsheet: budget.csv" in formatted
    assert "Marketing=6000" in formatted
    assert "Sales=12000" in formatted


def test_chunk_text_splits_large_content():
    text = "x" * 15000
    chunks = chunk_text(text, chunk_size=6000)
    assert len(chunks) == 3
    assert sum(len(chunk) for chunk in chunks) == 15000
