from enum import Enum

from app.agents.base import AgentContext


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskStore:
    def __init__(self):
        self._tasks: dict[str, AgentContext] = {}
        self._status: dict[str, TaskStatus] = {}

    def set(self, task_id: str, context: AgentContext, status: TaskStatus = TaskStatus.COMPLETED) -> None:
        self._tasks[task_id] = context
        self._status[task_id] = status

    def get(self, task_id: str) -> AgentContext | None:
        return self._tasks.get(task_id)

    def get_status(self, task_id: str) -> TaskStatus | None:
        return self._status.get(task_id)

    def mark_running(self, task_id: str) -> None:
        self._status[task_id] = TaskStatus.RUNNING

    def mark_failed(self, task_id: str) -> None:
        self._status[task_id] = TaskStatus.FAILED

    def all_task_ids(self) -> list[str]:
        return list(self._tasks.keys())
