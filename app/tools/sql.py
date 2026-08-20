import re

import asyncpg

from app.config import settings


class SQLValidationError(ValueError):
    """Raised when a query fails safety checks."""


_FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|GRANT|REVOKE|"
    r"COPY|EXECUTE|CALL|MERGE|REPLACE|ATTACH|DETACH)\b",
    re.IGNORECASE,
)
_MULTI_STATEMENT = re.compile(r";\s*\S")
_FROM_JOIN = re.compile(
    r"\b(?:FROM|JOIN)\s+([a-zA-Z_][\w]*)",
    re.IGNORECASE,
)


def validate_sql(
    sql: str,
    allowed_tables: set[str] | None = None,
    row_limit: int | None = None,
) -> str:
    """Ensure SQL is a single SELECT against allowlisted tables, with a row cap."""
    allowed = allowed_tables if allowed_tables is not None else settings.allowed_tables
    limit = row_limit if row_limit is not None else settings.sql_row_limit

    cleaned = sql.strip().rstrip(";")
    if not cleaned:
        raise SQLValidationError("SQL query is empty")

    if _MULTI_STATEMENT.search(cleaned + ";"):
        raise SQLValidationError("Multiple SQL statements are not allowed")

    if not re.match(r"(?is)^\s*(WITH\b|SELECT\b)", cleaned):
        raise SQLValidationError("Only SELECT (or WITH ... SELECT) queries are allowed")

    if _FORBIDDEN.search(cleaned):
        raise SQLValidationError("Query contains forbidden SQL keywords")

    tables = {m.group(1).lower() for m in _FROM_JOIN.finditer(cleaned)}
    unknown = tables - allowed
    if unknown:
        raise SQLValidationError(
            f"Query references non-allowlisted tables: {', '.join(sorted(unknown))}"
        )

    if not re.search(r"\bLIMIT\s+\d+\b", cleaned, re.IGNORECASE):
        cleaned = f"{cleaned} LIMIT {limit}"
    else:
        match = re.search(r"\bLIMIT\s+(\d+)\b", cleaned, re.IGNORECASE)
        if match and int(match.group(1)) > limit:
            cleaned = re.sub(
                r"\bLIMIT\s+\d+\b",
                f"LIMIT {limit}",
                cleaned,
                count=1,
                flags=re.IGNORECASE,
            )

    return cleaned


class SQLTool:
    def __init__(
        self,
        dsn: str | None = None,
        pool: asyncpg.Pool | None = None,
        allowed_tables: set[str] | None = None,
        row_limit: int | None = None,
    ):
        self.dsn = dsn or settings.database_url
        self.pool = pool
        self.allowed_tables = allowed_tables
        self.row_limit = row_limit

    async def connect(self) -> None:
        if self.pool is None:
            self.pool = await asyncpg.create_pool(
                self.dsn,
                min_size=settings.db_pool_min,
                max_size=settings.db_pool_max,
            )

    async def close(self) -> None:
        if self.pool is not None:
            await self.pool.close()
            self.pool = None

    async def query(self, sql: str, params=None):
        safe_sql = validate_sql(sql, self.allowed_tables, self.row_limit)
        if self.pool is None:
            conn = await asyncpg.connect(self.dsn)
            try:
                rows = await conn.fetch(safe_sql, *(params or []))
                return [dict(r) for r in rows]
            finally:
                await conn.close()

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(safe_sql, *(params or []))
            return [dict(r) for r in rows]
