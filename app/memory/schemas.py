from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Document(BaseModel):
    id: str
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    score: float | None = None


class TaskMemory(BaseModel):
    task_id: str
    goal: str
    email: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    summary: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
