import json
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import asyncpg

from app.agents.base import AgentContext
from app.config import settings

logger = logging.getLogger("app")


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskStore:
    """In-memory task store (fallback when Postgres is unavailable)."""

    def __init__(self):
        self._tasks: dict[str, AgentContext] = {}
        self._status: dict[str, TaskStatus] = {}
        self._errors: dict[str, str] = {}
        self._meta: dict[str, dict[str, Any]] = {}

    async def create(self, task_id: str, goal: str, email: str) -> None:
        self._status[task_id] = TaskStatus.PENDING
        self._meta[task_id] = {"goal": goal, "email": email}
        self._errors.pop(task_id, None)

    def set(
        self,
        task_id: str,
        context: AgentContext,
        status: TaskStatus = TaskStatus.COMPLETED,
        error: str | None = None,
    ) -> None:
        self._tasks[task_id] = context
        self._status[task_id] = status
        if error:
            self._errors[task_id] = error
        elif status != TaskStatus.FAILED:
            self._errors.pop(task_id, None)

    def get(self, task_id: str) -> AgentContext | None:
        return self._tasks.get(task_id)

    def get_status(self, task_id: str) -> TaskStatus | None:
        return self._status.get(task_id)

    def get_error(self, task_id: str) -> str | None:
        return self._errors.get(task_id)

    def get_meta(self, task_id: str) -> dict[str, Any]:
        return self._meta.get(task_id, {})

    def mark_running(self, task_id: str) -> None:
        self._status[task_id] = TaskStatus.RUNNING

    def mark_failed(self, task_id: str, error: str | None = None) -> None:
        self._status[task_id] = TaskStatus.FAILED
        if error:
            self._errors[task_id] = error

    def all_task_ids(self) -> list[str]:
        return list(self._status.keys())

    async def persist_create(self, task_id: str, goal: str, email: str) -> None:
        await self.create(task_id, goal, email)

    async def persist_update(
        self,
        task_id: str,
        status: TaskStatus,
        context: AgentContext | None = None,
        error: str | None = None,
    ) -> None:
        if context is not None:
            self.set(task_id, context, status=status, error=error)
        else:
            self._status[task_id] = status
            if error:
                self._errors[task_id] = error


class PostgresTaskStore(TaskStore):
    """Persists task status and results in Postgres, with an in-memory cache."""

    def __init__(self, pool: asyncpg.Pool):
        super().__init__()
        self.pool = pool

    async def persist_create(self, task_id: str, goal: str, email: str) -> None:
        await self.create(task_id, goal, email)
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO tasks (id, status, goal, email, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $5)
                ON CONFLICT (id) DO UPDATE
                SET status = EXCLUDED.status,
                    goal = EXCLUDED.goal,
                    email = EXCLUDED.email,
                    updated_at = EXCLUDED.updated_at
                """,
                task_id,
                TaskStatus.PENDING.value,
                goal,
                email,
                datetime.now(timezone.utc),
            )

    async def persist_update(
        self,
        task_id: str,
        status: TaskStatus,
        context: AgentContext | None = None,
        error: str | None = None,
    ) -> None:
        await super().persist_update(task_id, status, context=context, error=error)
        report = context.data.get("final_report") if context else None
        logs = json.dumps(context.logs if context else [])
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO tasks (id, status, goal, email, report, logs, error, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7, $8, $8)
                ON CONFLICT (id) DO UPDATE
                SET status = EXCLUDED.status,
                    report = COALESCE(EXCLUDED.report, tasks.report),
                    logs = EXCLUDED.logs,
                    error = EXCLUDED.error,
                    updated_at = EXCLUDED.updated_at
                """,
                task_id,
                status.value,
                context.user_goal if context else self.get_meta(task_id).get("goal"),
                context.user_email if context else self.get_meta(task_id).get("email"),
                report,
                logs,
                error,
                datetime.now(timezone.utc),
            )

    def get(self, task_id: str) -> AgentContext | None:
        cached = super().get(task_id)
        if cached is not None:
            return cached
        return None

    async def load(self, task_id: str) -> AgentContext | None:
        cached = self.get(task_id)
        if cached is not None:
            return cached

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, status, goal, email, report, logs, error FROM tasks WHERE id = $1",
                task_id,
            )
        if row is None:
            return None

        status = TaskStatus(row["status"])
        self._status[task_id] = status
        self._meta[task_id] = {"goal": row["goal"], "email": row["email"]}
        if row["error"]:
            self._errors[task_id] = row["error"]

        context = AgentContext(
            task_id=row["id"],
            user_goal=row["goal"] or "",
            user_email=row["email"] or "",
        )
        if row["report"]:
            context.data["final_report"] = row["report"]
        logs = row["logs"]
        if isinstance(logs, str):
            logs = json.loads(logs)
        context.logs = logs or []
        self._tasks[task_id] = context
        return context


async def build_task_store(pool: asyncpg.Pool | None) -> TaskStore:
    if pool is None:
        logger.warning("No DB pool available; using in-memory TaskStore")
        return TaskStore()
    return PostgresTaskStore(pool)
