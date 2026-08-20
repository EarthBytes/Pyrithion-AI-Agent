from .base import AgentContext, BaseAgent
from app.utils.prompts import RESEARCH_PROMPT
from app.utils.text import extract_filename_hint


class ResearchAgent(BaseAgent):
    name = "research"
    description = "Adds external/RAG context to the report."

    def __init__(self, rag_tool, llm_client):
        super().__init__(tools={"rag": rag_tool}, llm_client=llm_client)

    async def run(self, context: AgentContext) -> AgentContext:
        step = context.data["current_step"]
        task_desc = step["description"]
        filename_hint = context.data.get("source_document") or extract_filename_hint(
            context.user_goal
        )
        query = f"{context.user_goal}\n{task_desc}"

        docs = self.tools["rag"].search(query, filename_hint=filename_hint)
        prompt = f"""
{RESEARCH_PROMPT}

User question:
{context.user_goal}

Task:
{task_desc}

Requested source file (if any):
{filename_hint or "Not specified"}

Retrieved document excerpts:
{docs}
"""
        answer = await self.llm.call_text(prompt)
        context.data.setdefault("research_context", []).append(
            {
                "step": task_desc,
                "context": answer,
                "docs": docs,
                "filename_hint": filename_hint,
            }
        )
        context.logs.append(
            {
                "agent": self.name,
                "event": "research_context_added",
                "filename_hint": filename_hint,
                "doc_count": len(docs),
            }
        )
        return context
