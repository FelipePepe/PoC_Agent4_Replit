from __future__ import annotations

from fastapi import FastAPI, status
from fastapi.responses import JSONResponse

from core.models import ErrorResponse, TaskCreateRequest, TaskResult, TaskSummary
from core.services.tasks import InMemoryTaskService


def create_app(task_service: InMemoryTaskService | None = None) -> FastAPI:
    app = FastAPI(title='PoC Agent4 API', version='0.1.0')
    service = task_service or InMemoryTaskService()

    @app.post('/api/agent/tasks', status_code=status.HTTP_201_CREATED)
    def create_task(payload: TaskCreateRequest) -> dict:
        task = service.create_task(prompt=payload.prompt)
        return TaskResult(
            data=TaskSummary(taskId=task.task_id, status=task.status)
        ).model_dump(mode='json', by_alias=True)

    @app.get('/api/agent/tasks/{task_id}', response_model=None)
    def get_task(task_id: str):
        task = service.get_task(task_id)
        if task is None:
            error = ErrorResponse.from_values(code='TASK_NOT_FOUND', message='Task not found')
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content=error.model_dump(mode='json', by_alias=True),
            )
        return TaskResult(data=task).model_dump(mode='json', by_alias=True)

    @app.get('/health')
    def health() -> dict:
        return {'status': 'ok'}

    return app
