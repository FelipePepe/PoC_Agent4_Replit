from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from core.task_state import TaskStatus


class ResponseMeta(BaseModel):
    api_version: str = Field(default='v1', alias='apiVersion')

    model_config = ConfigDict(populate_by_name=True)


class TaskCreateRequest(BaseModel):
    prompt: str = Field(min_length=1)


class TaskSummary(BaseModel):
    task_id: str = Field(alias='taskId')
    status: TaskStatus

    model_config = ConfigDict(populate_by_name=True)


class TaskDetail(TaskSummary):
    progress: int = 0
    artifacts: list[str] = []


class ErrorDetail(BaseModel):
    code: str
    message: str
    retryable: bool = False


class TaskResult(BaseModel):
    data: TaskSummary | TaskDetail
    meta: ResponseMeta = Field(default_factory=ResponseMeta)


class ErrorResponse(BaseModel):
    error: ErrorDetail
    meta: ResponseMeta = Field(default_factory=ResponseMeta)

    @classmethod
    def from_values(
        cls,
        *,
        code: str,
        message: str,
        retryable: bool = False,
    ) -> 'ErrorResponse':
        return cls(error=ErrorDetail(code=code, message=message, retryable=retryable))
