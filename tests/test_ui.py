import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import create_app


@pytest.fixture
def web_client(monkeypatch):
    monkeypatch.setattr(settings, "api_key", "")
    app = create_app()
    app.state.sql_tool.pool = None
    with TestClient(app) as client:
        yield client


def test_home_page_renders(web_client):
    response = web_client.get("/")
    assert response.status_code == 200
    assert "Pyrithion AI" in response.text
    assert "source_document" not in response.text


def test_ask_form_submission(web_client):
    from app.routes import ui

    class ImmediateOrchestrator:
        async def run_task(self, task_id, user_goal, user_email, source_document=None):
            from app.agents.base import AgentContext

            ctx = AgentContext(task_id=task_id, user_goal=user_goal, user_email=user_email)
            ctx.data["final_report"] = "Done"
            return ctx

    ui.router.orchestrator = ImmediateOrchestrator()

    response = web_client.post(
        "/ask",
        data={
            "goal": "Summarise the onboarding guide",
            "email": "user@example.com",
        },
    )
    assert response.status_code == 200
    assert "Your report will be sent to" in response.text
    assert "user@example.com" in response.text


def test_ask_form_rejects_invalid_email(web_client):
    response = web_client.post(
        "/ask",
        data={"goal": "Hello", "email": "not-an-email"},
    )
    assert response.status_code == 400
    assert "valid email" in response.text
