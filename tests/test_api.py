from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from core.api import create_app
from core.services.tasks import InMemoryTaskService
from core.task_state import TaskStatus


# ── InMemoryTaskService ───────────────────────────────────────────────────── #

def test_in_memory_task_service_creates_queued_task() -> None:
    service = InMemoryTaskService()

    task = service.create_task(prompt='create hello world')

    assert task.task_id.startswith('task_')
    assert task.status is TaskStatus.QUEUED


def test_in_memory_task_service_returns_none_for_missing_task() -> None:
    service = InMemoryTaskService()

    assert service.get_task('task_missing') is None


# ── App route registration ────────────────────────────────────────────────── #

def test_create_app_registers_expected_routes() -> None:
    app = create_app()
    routes = {(method, route.path) for route in app.routes for method in getattr(route, 'methods', [])}

    assert ('POST', '/api/agent/tasks') in routes
    assert ('GET', '/api/agent/tasks/{task_id}') in routes
    assert ('GET', '/health') in routes


# ── HTTP endpoint behaviour ───────────────────────────────────────────────── #

@pytest.fixture()
def client() -> TestClient:
    return TestClient(create_app())


def test_health_endpoint_returns_ok(client: TestClient) -> None:
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}


def test_create_task_returns_201_with_task_id(client: TestClient) -> None:
    response = client.post('/api/agent/tasks', json={'prompt': 'build a calculator'})
    assert response.status_code == 201
    data = response.json()
    assert 'data' in data
    assert data['data']['taskId'].startswith('task_')
    assert data['data']['status'] == 'queued'


def test_create_task_uses_provided_service() -> None:
    service = InMemoryTaskService()
    client = TestClient(create_app(task_service=service))

    response = client.post('/api/agent/tasks', json={'prompt': 'test injection'})
    task_id = response.json()['data']['taskId']

    assert service.get_task(task_id) is not None


def test_get_task_returns_task(client: TestClient) -> None:
    created = client.post('/api/agent/tasks', json={'prompt': 'get me'})
    task_id = created.json()['data']['taskId']

    response = client.get(f'/api/agent/tasks/{task_id}')
    assert response.status_code == 200
    assert response.json()['data']['taskId'] == task_id


def test_get_task_returns_404_for_unknown_id(client: TestClient) -> None:
    response = client.get('/api/agent/tasks/task_nonexistent')
    assert response.status_code == 404
    data = response.json()
    assert data['error']['code'] == 'TASK_NOT_FOUND'
