import pytest
from fastapi.testclient import TestClient

from app.agents.base import AgentContext
from app.config import settings
from app.main import create_app
from app.orchestrator.state import TaskStatus


class ImmediateOrchestrator:
    async def run_task(
        self,
        task_id: str,
        user_goal: str,
        user_email: str,
        source_document: str | None = None,
    ) -> AgentContext:
        context = AgentContext(task_id=task_id, user_goal=user_goal, user_email=user_email)
        context.data["final_report"] = "Test report body"
        context.logs.append({"event": "done"})
        return context


class FailingOrchestrator:
    async def run_task(
        self,
        task_id: str,
        user_goal: str,
        user_email: str,
        source_document: str | None = None,
    ) -> AgentContext:
        raise RuntimeError("boom")


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(settings, "api_key", "")
    app = create_app()
    app.state.sql_tool.pool = None
    with TestClient(app) as test_client:
        test_client.app.state.orchestrator = ImmediateOrchestrator()
        from app.routes import tasks

        tasks.router.orchestrator = ImmediateOrchestrator()
        yield test_client


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_and_poll_task(client):
    from app.routes import tasks
    import time

    tasks.router.orchestrator = ImmediateOrchestrator()

    create = client.post(
        "/api/tasks",
        json={"goal": "Analyse energy", "email": "user@example.com"},
    )
    assert create.status_code == 202
    body = create.json()
    assert body["status"] == "pending"
    task_id = body["task_id"]

    result = None
    for _ in range(20):
        result = client.get(f"/api/result/{task_id}")
        if result.json()["status"] in {TaskStatus.COMPLETED.value, TaskStatus.FAILED.value}:
            break
        time.sleep(0.05)

    assert result is not None
    payload = result.json()
    assert payload["status"] == TaskStatus.COMPLETED.value
    assert payload["report"] == "Test report body"


def test_unknown_task_returns_404(client):
    response = client.get("/api/result/does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"] == "not_found"


def test_api_key_required(monkeypatch):
    monkeypatch.setattr(settings, "api_key", "secret-key")
    app = create_app()
    with TestClient(app) as test_client:
        denied = test_client.post(
            "/api/tasks",
            json={"goal": "x", "email": "user@example.com"},
        )
        assert denied.status_code == 401

        from app.routes import tasks

        tasks.router.orchestrator = ImmediateOrchestrator()
        allowed = test_client.post(
            "/api/tasks",
            headers={"X-API-Key": "secret-key"},
            json={"goal": "x", "email": "user@example.com"},
        )
        assert allowed.status_code == 202


def test_failed_task_surfaces_error(client):
    from app.routes import tasks
    import time

    tasks.router.orchestrator = FailingOrchestrator()

    create = client.post(
        "/api/tasks",
        json={"goal": "Analyse energy", "email": "user@example.com"},
    )
    task_id = create.json()["task_id"]

    payload = None
    for _ in range(20):
        response = client.get(f"/api/result/{task_id}")
        payload = response.json()
        if payload["status"] == TaskStatus.FAILED.value:
            break
        time.sleep(0.05)

    assert payload["status"] == TaskStatus.FAILED.value
    assert "boom" in payload.get("error", "")
