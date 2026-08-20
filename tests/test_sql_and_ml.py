import pytest

from app.agents.ml import extract_numeric_series
from app.tools.sql import SQLValidationError, validate_sql


def test_validate_sql_allows_select_and_adds_limit():
    sql = validate_sql("SELECT value FROM energy_usage", row_limit=10)
    assert sql.upper().endswith("LIMIT 10")


def test_validate_sql_rejects_delete():
    with pytest.raises(SQLValidationError):
        validate_sql("DELETE FROM energy_usage")


def test_validate_sql_rejects_unknown_table():
    with pytest.raises(SQLValidationError, match="non-allowlisted"):
        validate_sql("SELECT * FROM secrets")


def test_validate_sql_rejects_multi_statement():
    with pytest.raises(SQLValidationError, match="Multiple"):
        validate_sql("SELECT 1; DROP TABLE users")


def test_validate_sql_caps_existing_limit():
    sql = validate_sql("SELECT amount FROM revenue LIMIT 9999", row_limit=50)
    assert "LIMIT 50" in sql.upper()


def test_extract_numeric_series_picks_amount():
    rows = [{"region": "EMEA", "amount": 10.0}, {"region": "AMER", "amount": 20.5}]
    column, values = extract_numeric_series(rows)
    assert column == "amount"
    assert values == [10.0, 20.5]


def test_extract_numeric_series_empty_rows():
    with pytest.raises(ValueError, match="No data rows"):
        extract_numeric_series([])
