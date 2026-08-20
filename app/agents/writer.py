from .base import AgentContext, BaseAgent
from app.utils.prompts import WRITER_PROMPT_ANALYTICS, WRITER_PROMPT_DOCUMENT


class WriterAgent(BaseAgent):
    name = "writer"
    description = "Generates the final report text."

    async def run(self, context: AgentContext) -> AgentContext:
        data_results = context.data.get("data_results", [])
        ml_summaries = context.data.get("ml_summaries", [])
        research_context = context.data.get("research_context", [])

        document_only = bool(research_context) and not data_results
        writer_prompt = WRITER_PROMPT_DOCUMENT if document_only else WRITER_PROMPT_ANALYTICS

        prompt = f"""
{writer_prompt}

User goal:
{context.user_goal}

Data results:
{data_results}

ML summaries:
{ml_summaries}

Research context (primary source for document questions):
{research_context}
"""
        report = await self.llm.call_text(prompt)
        context.data["final_report"] = report
        context.logs.append({"agent": self.name, "event": "report_generated"})
        return context
