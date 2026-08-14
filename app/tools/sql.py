import asyncpg

class SQLTool:
    def __init__(self, dsn):
        self.dsn = dsn

    async def query(self, sql: str, params=None):
        conn = await asyncpg.connect(self.dsn)
        try:
            rows = await conn.fetch(sql, * (params or []))
            return [dict(r) for r in rows]
        finally:
            await conn.close()
