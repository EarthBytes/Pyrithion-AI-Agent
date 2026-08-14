from fastapi import APIRouter
from pydantic import BaseModel, EmailStr
from app.orchestrator.orchestrator import Orchestrator
from app.orchestrator.state import TaskStatus, TaskStore
from app.utils.id_generator import generate_task_id

router = APIRouter()

class TaskRequest(BaseModel):
    goal: str
    email: EmailStr

@router.post("/tasks")
async def create_task(req: TaskRequest):
    task_id = generate_task_id()
    orchestrator: Orchestrator = router.orchestrator
    task_store: TaskStore = router.task_store

    task_store.mark_running(task_id)
    try:
        context = await orchestrator.run_task(task_id, req.goal, str(req.email))
        task_store.set(task_id, context, status=TaskStatus.COMPLETED)
    except Exception:
        task_store.mark_failed(task_id)
        raise

    return {"task_id": task_id, "status": TaskStatus.COMPLETED}


@router.get("/result/{task_id}")
async def get_result(task_id: str):
    task_store: TaskStore = router.task_store
    context = task_store.get(task_id)
    status = task_store.get_status(task_id)

    if not context:
        return {"status": status.value if status else "unknown_task"}

    return {
        "status": status.value if status else TaskStatus.COMPLETED.value,
        "goal": context.user_goal,
        "email": context.user_email,
        "report": context.data.get("final_report"),
        "logs": context.logs,
    }
