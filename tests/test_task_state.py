import pytest

from core.state import create_initial_state
from core.task_state import TaskStatus, TaskStateMachine, TaskStateTransitionError


def test_create_initial_state_contains_full_base_shape() -> None:
    state = create_initial_state(task_id='task_123')

    assert state['messages'] == []
    assert state['tool_calls'] == []
    assert state['error_count'] == 0
    assert state['current_model'] == 'claude-sonnet'
    assert state['task_id'] == 'task_123'
    assert state['subtasks'] == []
    assert state['active_agent'] == 'supervisor'
    assert state['parallel_results'] == {}
    assert state['active_instructions'] == []
    assert state['consecutive_errors'] == 0
    assert state['model_switches'] == 0
    assert state['snapshot_id'] is None


def test_state_machine_allows_documented_transition() -> None:
    machine = TaskStateMachine()

    next_state = machine.transition(TaskStatus.QUEUED, TaskStatus.RUNNING)

    assert next_state is TaskStatus.RUNNING


@pytest.mark.parametrize(
    ('source', 'target'),
    [
        (TaskStatus.QUEUED, TaskStatus.COMPLETED),
        (TaskStatus.COMPLETED, TaskStatus.RUNNING),
        (TaskStatus.CANCELLED, TaskStatus.RUNNING),
    ],
)
def test_state_machine_rejects_invalid_transitions(source: TaskStatus, target: TaskStatus) -> None:
    machine = TaskStateMachine()

    with pytest.raises(TaskStateTransitionError):
        machine.transition(source, target)


def test_terminal_states_are_completed_and_cancelled() -> None:
    machine = TaskStateMachine()

    assert machine.is_terminal(TaskStatus.COMPLETED) is True
    assert machine.is_terminal(TaskStatus.CANCELLED) is True
    assert machine.is_terminal(TaskStatus.RUNNING) is False
