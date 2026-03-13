from __future__ import annotations

from typing import Any, TypedDict


class AgentState(TypedDict):
    messages: list[Any]
    tool_calls: list[Any]
    error_count: int
    current_model: str
    task_id: str
    subtasks: list[Any]
    active_agent: str
    parallel_results: dict[str, Any]
    active_instructions: list[str]
    consecutive_errors: int
    model_switches: int
    snapshot_id: str | None


DEFAULT_MODEL = 'claude-sonnet'
DEFAULT_AGENT = 'supervisor'


def create_initial_state(task_id: str) -> AgentState:
    return AgentState(
        messages=[],
        tool_calls=[],
        error_count=0,
        current_model=DEFAULT_MODEL,
        task_id=task_id,
        subtasks=[],
        active_agent=DEFAULT_AGENT,
        parallel_results={},
        active_instructions=[],
        consecutive_errors=0,
        model_switches=0,
        snapshot_id=None,
    )
