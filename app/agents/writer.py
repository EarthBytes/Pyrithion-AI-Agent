from .base import BaseAgent, AgentContext

WRITER_PROMPT = """
You are a report-writing agent for an email report generator.
You receive:
- user goal
- data results (SQL outputs)
- ML summaries (anomalies/trends)
- optional research context

You must produce a clear, structured report with sections:
1. Overview
2. Data Summary
3. Anomaly / Trend Analysis
4. External Context (if available)
5. Recommendations

Write in concise, professional language suitable for email.
"""

class WriterAgent(BaseAgent):
    name = "writer"
    description = "Generates the final report text."

    async def run(self, context: AgentContext) -> AgentContext:
        data_results = context.data.get("data_results", [])
        ml_summaries = context.data.get("ml_summaries", [])
        research_context = context.data.get("research_context", [])

        prompt = f"""
{WRITER_PROMPT}

User goal:
{context.user_goal}

Data results:
{data_results}

ML summaries:
{ml_summaries}

Research context:
{research_context}
"""
        report = await self.llm.call_text(prompt)
        context.data["final_report"] = report
        context.logs.append({"agent": self.name, "event": "report_generated"})
        return context
