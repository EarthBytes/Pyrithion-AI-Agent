from .base import BaseAgent, AgentContext

RESEARCH_PROMPT = """
You are a context-enrichment agent.
You receive a description of the analysis and retrieved documents.
You must add relevant external context (benchmarks, best practices) grounded in the docs.

Return a concise, source-grounded summary.
"""

class ResearchAgent(BaseAgent):
    name = "research"
    description = "Adds external/RAG context to the report."

    def __init__(self, rag_tool, llm_client):
        super().__init__(tools={"rag": rag_tool}, llm_client=llm_client)

    async def run(self, context: AgentContext) -> AgentContext:
        step = context.data["current_step"]
        task_desc = step["description"]

        docs = self.tools["rag"].search(task_desc)
        prompt = f"""
{RESEARCH_PROMPT}

Task:
{task_desc}

Retrieved docs:
{docs}
"""
        answer = await self.llm.call_text(prompt)
        context.data.setdefault("research_context", []).append(
            {"step": task_desc, "context": answer, "docs": docs}
        )
        context.logs.append({"agent": self.name, "event": "research_context_added"})
        return context
