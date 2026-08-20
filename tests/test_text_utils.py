from app.utils.text import extract_filename_hint


def test_extract_filename_hint_from_verdant_financials():
    goal = "Tell me the marketing budget from verdant_financials sheet"
    assert extract_filename_hint(goal) == "verdant_financials"
