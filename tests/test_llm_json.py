from app.models.llm_client import LLMClient


def test_parse_json_allows_control_characters_in_strings():
    raw = """{
  "steps": [
    {"agent": "research", "description": "Find marketing budget
and operating profit"}
  ]
}"""
    parsed = LLMClient._parse_json(raw)
    assert parsed["steps"][0]["agent"] == "research"
