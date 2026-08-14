from fastapi import APIRouter
from pydantic import BaseModel
from app.orchestrator.orchestrator import Orchestrator
from app.utils.id_generator import generate_task_id

router = APIRouter()
TASK_STORE = {}

class TaskRequest(BaseModel):
    goal: str
    email: str

@router.post("/tasks")
async def create_task(req: TaskRequest):
    task_id = generate_task_id()
    orchestrator: Orchestrator = router.orchestrator

    context = await orchestrator.run_task(task_id, req.goal, req.email)
    TASK_STORE[task_id] = context
    return {"task_id": task_id}

@router.get("/result/{task_id}")
async def get_result(task_id: str):
    context = TASK_STORE.get(task_id)
    if not context:
        return {"status": "unknown_task"}
    return {
        "goal": context.user_goal,
        "email": context.user_email,
        "report": context.data.get("final_report"),
        "logs": context.logs,
    }
