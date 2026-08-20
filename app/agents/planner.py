from .base import BaseAgent, AgentContext

PLANNER_PROMPT = """
You are a planning agent for an email report generator.
Given a user's goal, break it into ordered steps.

Available agents:
- data: fetch and aggregate data via SQL (only for database/analytics questions)
- ml: run anomaly/trend analysis on numeric query results
- research: find answers from uploaded documents and knowledge base (policies, guides, reports)
- writer: write the final report
- executor: deliver the report via email

Rules:
- For document, policy, Google Drive, Google Sheets, CSV, or spreadsheet questions: use research -> writer -> executor ONLY
- Never use the data or ml agents for spreadsheet or document questions — they cannot read Drive files
- For database/analytics questions about Postgres tables: use data (and ml if trends/anomalies are needed) -> writer -> executor
- research can be combined with data/ml only when the user explicitly asks for both documents and database analytics
- Always end with writer then executor

Return JSON:
{"steps": [
  {"agent": "research", "description": "..."},
  {"agent": "writer", "description": "..."},
  {"agent": "executor", "description": "..."}
]}
"""

class PlannerAgent(BaseAgent):
    name = "planner"
    description = "Plans steps for email report generation."

    async def run(self, context: AgentContext) -> AgentContext:
        prompt = f"""
{PLANNER_PROMPT}

User goal:
{context.user_goal}
"""
        plan = await self.llm.call_json(prompt)
        context.data["plan"] = plan["steps"]
        context.logs.append({"agent": self.name, "event": "plan_created", "plan": plan})
        return context
