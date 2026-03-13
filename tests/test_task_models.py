from __future__ import annotations

from core.models import ErrorResponse, TaskDetail, TaskResult, TaskSummary
from core.task_state import TaskStatus


def test_task_summary_serializes_expected_fields() -> None:
    summary = TaskSummary(task_id='task_1', status=TaskStatus.QUEUED)

    assert summary.task_id == 'task_1'
    assert summary.status is TaskStatus.QUEUED


def test_task_detail_defaults_progress_and_artifacts() -> None:
    detail = TaskDetail(task_id='task_2', status=TaskStatus.RUNNING)

    assert detail.progress == 0
    assert detail.artifacts == []


def test_task_result_wraps_detail_with_api_version() -> None:
    result = TaskResult(data=TaskSummary(task_id='task_3', status=TaskStatus.COMPLETED))

    assert result.meta.api_version == 'v1'
    assert result.data.task_id == 'task_3'


def test_error_response_exposes_stable_contract() -> None:
    error = ErrorResponse.from_values(code='TASK_NOT_FOUND', message='Task not found')

    assert error.error.code == 'TASK_NOT_FOUND'
    assert error.error.retryable is False
    assert error.meta.api_version == 'v1'
