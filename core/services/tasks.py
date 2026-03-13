from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

from core.models import TaskDetail
from core.task_state import TaskStatus


@dataclass(slots=True)
class InMemoryTaskService:
    tasks: dict[str, TaskDetail] = field(default_factory=dict)

    def create_task(self, *, prompt: str) -> TaskDetail:
        _ = prompt
        task_id = f'task_{uuid4().hex[:12]}'
        task = TaskDetail(taskId=task_id, status=TaskStatus.QUEUED)
        self.tasks[task_id] = task
        return task

    def get_task(self, task_id: str) -> TaskDetail | None:
        return self.tasks.get(task_id)
