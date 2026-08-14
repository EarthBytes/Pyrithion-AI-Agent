from .base import BaseAgent, AgentContext

PLANNER_PROMPT = """
You are a planning agent for an email report generator.
Given a user's goal, break it into ordered steps.
Use these agents:
- data: fetch and aggregate data via SQL
- ml: run anomaly/trend analysis
- research: optional external/RAG context
- writer: write the final report
- executor: deliver the report via email

Always include writer and executor as the last two steps.

Return JSON:
{"steps": [
  {"agent": "data", "description": "..."},
  {"agent": "ml", "description": "..."},
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
