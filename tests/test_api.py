from __future__ import annotations

from core.api import create_app
from core.services.tasks import InMemoryTaskService
from core.task_state import TaskStatus


def test_in_memory_task_service_creates_queued_task() -> None:
    service = InMemoryTaskService()

    task = service.create_task(prompt='create hello world')

    assert task.task_id.startswith('task_')
    assert task.status is TaskStatus.QUEUED


def test_in_memory_task_service_returns_none_for_missing_task() -> None:
    service = InMemoryTaskService()

    assert service.get_task('task_missing') is None


def test_create_app_registers_expected_routes() -> None:
    app = create_app()
    routes = {(method, route.path) for route in app.routes for method in getattr(route, 'methods', [])}

    assert ('POST', '/api/agent/tasks') in routes
    assert ('GET', '/api/agent/tasks/{task_id}') in routes
    assert ('GET', '/health') in routes
