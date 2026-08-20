import pytest

from app.agents.base import AgentContext
from app.orchestrator.orchestrator import Orchestrator


class StubAgent:
    def __init__(self, name: str, handler):
        self.name = name
        self.handler = handler

    async def run(self, context: AgentContext) -> AgentContext:
        result = self.handler(context)
        if hasattr(result, "__await__"):
            return await result
        return result


@pytest.mark.asyncio
async def test_orchestrator_strips_sql_for_document_questions(filesystem_tool):
    captured: list[str] = []

    async def planner_run(context):
        context.data["plan"] = [
            {"agent": "data", "description": "Run SQL"},
            {"agent": "research", "description": "Search docs"},
            {"agent": "writer", "description": "Write report"},
        ]
        return context

    async def research_run(context):
        captured.append("research")
        context.data["research_context"] = [{"context": "Marketing=6000"}]
        return context

    async def writer_run(context):
        context.data["final_report"] = "Budget is £6000"
        return context

    agents = {
        "planner": StubAgent("planner", planner_run),
        "data": StubAgent("data", lambda ctx: ctx),
        "research": StubAgent("research", research_run),
        "writer": StubAgent("writer", writer_run),
    }
    orchestrator = Orchestrator(agents=agents, filesystem_tool=filesystem_tool)

    context = await orchestrator.run_task(
        "task-2",
        "What is the marketing budget in the spreadsheet?",
        "user@example.com",
    )

    assert captured == ["research"]
    assert "final_report" in context.data


@pytest.mark.asyncio
async def test_orchestrator_runs_plan_and_saves_report(filesystem_tool):
    async def planner_run(context):
        context.data["plan"] = [
            {"agent": "writer", "description": "Write report"},
        ]
        return context

    async def writer_run(context):
        context.data["final_report"] = "Saved report"
        return context

    agents = {
        "planner": StubAgent("planner", planner_run),
        "writer": StubAgent("writer", writer_run),
    }
    orchestrator = Orchestrator(agents=agents, filesystem_tool=filesystem_tool)

    context = await orchestrator.run_task("task-1", "Test goal", "user@example.com")

    assert context.data["final_report"] == "Saved report"
    assert filesystem_tool.read_report("task-1") == "Saved report"
    assert any(log.get("event") == "report_saved" for log in context.logs)
