from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class TaskStatus(StrEnum):
    QUEUED = 'queued'
    RUNNING = 'running'
    BLOCKED = 'blocked'
    FAILED = 'failed'
    ROLLING_BACK = 'rolling_back'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'


class TaskStateTransitionError(ValueError):
    """Raised when a task state transition is not allowed."""


@dataclass(slots=True)
class TaskStateMachine:
    allowed_transitions: dict[TaskStatus, set[TaskStatus]] = field(
        default_factory=lambda: {
            TaskStatus.QUEUED: {TaskStatus.RUNNING, TaskStatus.CANCELLED},
            TaskStatus.RUNNING: {
                TaskStatus.COMPLETED,
                TaskStatus.FAILED,
                TaskStatus.BLOCKED,
                TaskStatus.ROLLING_BACK,
                TaskStatus.CANCELLED,
            },
            TaskStatus.BLOCKED: {
                TaskStatus.RUNNING,
                TaskStatus.ROLLING_BACK,
                TaskStatus.FAILED,
                TaskStatus.CANCELLED,
            },
            TaskStatus.FAILED: {
                TaskStatus.RUNNING,
                TaskStatus.ROLLING_BACK,
                TaskStatus.CANCELLED,
            },
            TaskStatus.ROLLING_BACK: {
                TaskStatus.RUNNING,
                TaskStatus.BLOCKED,
                TaskStatus.FAILED,
                TaskStatus.CANCELLED,
            },
            TaskStatus.COMPLETED: set(),
            TaskStatus.CANCELLED: set(),
        }
    )

    def transition(self, source: TaskStatus, target: TaskStatus) -> TaskStatus:
        if target not in self.allowed_transitions[source]:
            raise TaskStateTransitionError(
                f'Invalid task state transition: {source} -> {target}'
            )
        return target

    @staticmethod
    def is_terminal(status: TaskStatus) -> bool:
        return status in {TaskStatus.COMPLETED, TaskStatus.CANCELLED}
