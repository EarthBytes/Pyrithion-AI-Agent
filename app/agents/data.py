from .base import BaseAgent, AgentContext

DATA_PROMPT = """
You are a data agent.
You receive a description of what data is needed and a DB schema.
You must output a single SQL query that is:
- SELECT-only
- safe (no DROP/UPDATE/DELETE)
- appropriate for analytics.

Return JSON:
{"sql": "..."}
"""

class DataAgent(BaseAgent):
    name = "data"
    description = "Generates and executes SQL for analytics."

    def __init__(self, sql_tool, llm_client, schema_text: str):
        super().__init__(tools={"sql": sql_tool}, llm_client=llm_client)
        self.schema_text = schema_text

    async def run(self, context: AgentContext) -> AgentContext:
        step = context.data["current_step"]
        task_desc = step["description"]

        prompt = f"""
{DATA_PROMPT}

DB schema:
{self.schema_text}

Task:
{task_desc}
"""
        sql_json = await self.llm.call_json(prompt)
        sql = sql_json["sql"]

        rows = await self.tools["sql"].query(sql)
        context.data.setdefault("data_results", []).append(
            {"step": task_desc, "sql": sql, "rows": rows}
        )
        context.logs.append({"agent": self.name, "event": "sql_executed", "sql": sql})
        return context
