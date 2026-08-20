import asyncio
import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr

from app.auth import require_api_key
from app.errors import AppError
from app.orchestrator.orchestrator import Orchestrator
from app.orchestrator.state import TaskStatus, TaskStore
from app.utils.id_generator import generate_task_id

router = APIRouter(dependencies=[Depends(require_api_key)])
logger = logging.getLogger("app")


class TaskRequest(BaseModel):
    goal: str
    email: EmailStr


async def _run_in_background(
    task_id: str,
    goal: str,
    email: str,
    orchestrator: Orchestrator,
    task_store: TaskStore,
    source_document: str | None = None,
) -> None:
    try:
        await task_store.persist_update(task_id, TaskStatus.RUNNING)
        context = await orchestrator.run_task(
            task_id, goal, email, source_document=source_document
        )
        await task_store.persist_update(task_id, TaskStatus.COMPLETED, context=context)
    except Exception as exc:
        logger.exception("Task %s failed", task_id)
        await task_store.persist_update(
            task_id,
            TaskStatus.FAILED,
            error=str(exc),
        )


@router.post("/tasks", status_code=202)
async def create_task(req: TaskRequest):
    task_id = generate_task_id()
    orchestrator: Orchestrator = router.orchestrator
    task_store: TaskStore = router.task_store

    await task_store.persist_create(task_id, req.goal, str(req.email))
    asyncio.create_task(
        _run_in_background(task_id, req.goal, str(req.email), orchestrator, task_store)
    )
    return {"task_id": task_id, "status": TaskStatus.PENDING}


@router.get("/result/{task_id}")
async def get_result(task_id: str):
    task_store: TaskStore = router.task_store

    context = task_store.get(task_id)
    if context is None and hasattr(task_store, "load"):
        context = await task_store.load(task_id)

    status = task_store.get_status(task_id)
    if status is None and context is None:
        raise AppError("Unknown task_id", code="not_found", status_code=404)

    meta = task_store.get_meta(task_id)
    payload = {
        "status": status.value if status else TaskStatus.COMPLETED.value,
        "goal": context.user_goal if context else meta.get("goal"),
        "email": context.user_email if context else meta.get("email"),
        "report": context.data.get("final_report") if context else None,
        "logs": context.logs if context else [],
    }
    error = task_store.get_error(task_id)
    if error:
        payload["error"] = error
    return payload
