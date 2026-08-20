import pytest

from app.agents.base import AgentContext


@pytest.mark.asyncio
async def test_planner_creates_plan(planner_agent, agent_context):
    result = await planner_agent.run(agent_context)

    assert "plan" in result.data
    assert len(result.data["plan"]) >= 2
    assert result.data["plan"][-1]["agent"] == "executor"


@pytest.mark.asyncio
async def test_data_agent_runs_sql(data_agent, agent_context):
    agent_context.data["current_step"] = {"description": "Fetch energy usage"}
    result = await data_agent.run(agent_context)

    assert result.data["data_results"]
    assert result.data["data_results"][0]["rows"][0]["value"] == 80.0


@pytest.mark.asyncio
async def test_ml_agent_summarizes_amount_column(ml_agent, agent_context):
    agent_context.data["data_results"] = [
        {
            "step": "fetch",
            "sql": "SELECT amount FROM revenue",
            "rows": [{"amount": 80}, {"amount": 200}],
        }
    ]
    agent_context.data["current_step"] = {"description": "Detect anomalies"}
    result = await ml_agent.run(agent_context)

    assert result.data["ml_summaries"]
    assert result.data["ml_summaries"][0]["column"] == "amount"
    assert "anomaly" in result.data["ml_summaries"][0]["summary"].lower()


@pytest.mark.asyncio
async def test_research_agent_adds_context(research_agent, agent_context):
    agent_context.data["current_step"] = {"description": "Add benchmarks"}
    result = await research_agent.run(agent_context)

    assert result.data["research_context"]


@pytest.mark.asyncio
async def test_writer_generates_report(writer_agent, agent_context):
    agent_context.data["data_results"] = [{"rows": [{"value": 1}]}]
    agent_context.data["ml_summaries"] = [{"summary": "No anomalies"}]
    result = await writer_agent.run(agent_context)

    assert result.data["final_report"]
    assert "Report" in result.data["final_report"]


@pytest.mark.asyncio
async def test_executor_sends_email(executor_agent, agent_context):
    agent_context.data["final_report"] = "Final report body"
    agent_context.data["current_step"] = {"description": "Send email"}
    result = await executor_agent.run(agent_context)

    sent = executor_agent.tools["email"].sent
    assert sent
    assert sent[0]["to"] == "user@example.com"
    assert sent[0]["body"] == "Final report body"
