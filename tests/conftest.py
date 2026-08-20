import pytest

from app.agents.base import AgentContext
from app.agents.data import DataAgent
from app.agents.executor import ExecutorAgent
from app.agents.ml import MLAgent
from app.agents.planner import PlannerAgent
from app.agents.research import ResearchAgent
from app.agents.writer import WriterAgent
from app.tools.filesystem import FilesystemTool
from app.tools.ml_tools import MLTools


class FakeLLM:
    async def call_json(self, prompt: str) -> dict:
        lowered = prompt.lower()
        if "planning agent" in lowered or '"steps"' in lowered:
            return {
                "steps": [
                    {"agent": "data", "description": "Fetch energy usage"},
                    {"agent": "ml", "description": "Detect anomalies"},
                    {"agent": "writer", "description": "Write report"},
                    {"agent": "executor", "description": "Email report"},
                ]
            }
        if "data agent" in lowered or "sql" in lowered:
            return {"sql": "SELECT value FROM energy_usage LIMIT 5"}
        if "executor agent" in lowered or "subject" in lowered:
            return {"subject": "Your analytics report"}
        return {}

    async def call_text(self, prompt: str) -> str:
        if "ml analysis agent" in prompt.lower():
            return "Detected one anomaly spike in recent values."
        if "context-enrichment agent" in prompt.lower():
            return "External benchmarks suggest usage is within normal range."
        if "report-writing agent" in prompt.lower():
            return "# Report\n\nOverview\n\nData shows stable usage with one spike."
        return "Summary text"


class FakeSQLTool:
    async def query(self, sql: str, params=None):
        return [{"value": 80.0}, {"value": 85.0}, {"value": 200.0}]


class FakeEmailTool:
    def __init__(self):
        self.sent = []

    def send_email(self, to: str, subject: str, body: str) -> None:
        self.sent.append({"to": to, "subject": subject, "body": body})


class FakeRAGTool:
    def search(self, query: str):
        return [{"text": "Benchmark doc", "score": 0.9, "metadata": {}}]


@pytest.fixture
def fake_llm():
    return FakeLLM()


@pytest.fixture
def agent_context():
    return AgentContext(
        task_id="test-task",
        user_goal="Analyse energy usage and email me a report",
        user_email="user@example.com",
    )


@pytest.fixture
def planner_agent(fake_llm):
    return PlannerAgent(llm_client=fake_llm)


@pytest.fixture
def data_agent(fake_llm):
    return DataAgent(
        sql_tool=FakeSQLTool(),
        llm_client=fake_llm,
        schema_text="energy_usage(value)",
    )


@pytest.fixture
def ml_agent(fake_llm):
    return MLAgent(ml_tools=MLTools(), llm_client=fake_llm)


@pytest.fixture
def research_agent(fake_llm):
    return ResearchAgent(rag_tool=FakeRAGTool(), llm_client=fake_llm)


@pytest.fixture
def writer_agent(fake_llm):
    return WriterAgent(llm_client=fake_llm)


@pytest.fixture
def executor_agent(fake_llm):
    return ExecutorAgent(email_tool=FakeEmailTool(), llm_client=fake_llm)


@pytest.fixture
def filesystem_tool(tmp_path):
    return FilesystemTool(base_dir=tmp_path)
