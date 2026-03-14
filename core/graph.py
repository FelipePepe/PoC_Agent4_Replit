"""LangGraph graph — Fase 1: ReAct loop with sandboxed tools.

Graph topology:
    START → supervisor → tool_executor → supervisor → … → verifier → END
                  ↓ (no tool calls or max iterations reached)
               verifier → END

The supervisor node binds the LLM to the sandboxed tools and decides, via
conditional routing, whether to execute tool calls or hand off to verifier.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import ToolMessage
from langgraph.graph import END, StateGraph

from core.state import AgentState

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = 'claude-sonnet-4-5'


@dataclass(slots=True)
class GraphConfig:
    model_name: str = field(default=_DEFAULT_MODEL)


def build_llm(cfg: GraphConfig | None = None) -> BaseChatModel:
    """Instantiate the primary LLM.  Extracted so tests can patch it easily."""
    resolved = cfg or GraphConfig()
    return ChatAnthropic(model=resolved.model_name)  # type: ignore[call-arg]


# ── Node factories ─────────────────────────────────────────────────────────── #


def _make_supervisor_node(bound_llm: BaseChatModel):
    """Return a supervisor node function closed over *bound_llm*."""

    def supervisor_node(state: AgentState) -> dict:
        """Calls the LLM (with tools bound) and appends the response."""
        logger.info(
            'supervisor_node — task_id=%s messages=%d tool_calls_so_far=%d',
            state.get('task_id', '?'),
            len(state.get('messages', [])),
            len(state.get('tool_calls', [])),
        )
        response = bound_llm.invoke(state['messages'])
        logger.info(
            'supervisor_node response — has_tool_calls=%s',
            bool(getattr(response, 'tool_calls', None)),
        )
        return {
            'messages': state['messages'] + [response],
            'active_agent': 'supervisor',
        }

    return supervisor_node


def _make_tool_executor_node(tool_map: dict):
    """Return a tool-executor node function closed over *tool_map*."""

    def tool_executor_node(state: AgentState) -> dict:
        """Execute every tool call present in the last AIMessage."""
        last = state['messages'][-1]
        tool_results: list[ToolMessage] = []
        new_tool_calls = list(state.get('tool_calls') or [])

        for tc in last.tool_calls:
            tool = tool_map.get(tc['name'])
            logger.info('tool_executor — executing tool=%s args=%s', tc['name'], tc['args'])
            result = tool.invoke(tc['args']) if tool is not None else f"Tool '{tc['name']}' not found."
            tool_results.append(ToolMessage(content=str(result), tool_call_id=tc['id']))
            new_tool_calls.append(tc)

        return {
            'messages': state['messages'] + tool_results,
            'tool_calls': new_tool_calls,
        }

    return tool_executor_node


def _verifier_node(state: AgentState) -> dict:
    """Validate / summarise the completed task and mark it done."""
    logger.info(
        'verifier_node — task_id=%s total_tool_calls=%d',
        state.get('task_id', '?'),
        len(state.get('tool_calls') or []),
    )
    return {'active_agent': 'verifier'}


def _make_router(max_iterations: int):
    """Return a routing function closed over *max_iterations*."""

    def route_after_supervisor(state: AgentState) -> Literal['tool_executor', 'verifier']:
        last = state['messages'][-1]
        has_tool_calls = bool(getattr(last, 'tool_calls', None))
        iterations_done = len(state.get('tool_calls') or [])
        if has_tool_calls and iterations_done < max_iterations:
            return 'tool_executor'
        return 'verifier'

    return route_after_supervisor


# ── Public API ─────────────────────────────────────────────────────────────── #


def _resolve_app_config(app_config_workspace: Path | str | None):
    """Build an AppConfig from an optional workspace path."""
    from core.config import create_default_config

    if app_config_workspace is not None:
        workspace = Path(app_config_workspace)
        return create_default_config(project_root=workspace.parent, workspace_dir=workspace)
    return create_default_config(project_root=Path('.'))


def build_graph(
    cfg: GraphConfig | None = None,
    *,
    app_config_workspace: Path | str | None = None,
    max_iterations: int | None = None,
):
    """Compile and return the ReAct LangGraph graph.

    Parameters
    ----------
    cfg:
        LangGraph model configuration (model name, etc.).
    app_config_workspace:
        Path to the sandbox workspace directory fed to AppConfig / tools.
        When *None* the default ``workspace/agent_sandbox`` inside the
        current project root is used.
    max_iterations:
        Maximum tool-execution rounds before forcing termination.
        Defaults to ``AppConfig.max_agent_iterations`` (10).
    """
    from core.tools import make_tools

    llm = build_llm(cfg or GraphConfig())
    app_config = _resolve_app_config(app_config_workspace)
    resolved_max = max_iterations if max_iterations is not None else app_config.max_agent_iterations

    tools = make_tools(app_config)
    bound_llm = llm.bind_tools(tools)

    builder = StateGraph(AgentState)
    builder.add_node('supervisor', _make_supervisor_node(bound_llm))
    builder.add_node('tool_executor', _make_tool_executor_node({t.name: t for t in tools}))
    builder.add_node('verifier', _verifier_node)
    builder.set_entry_point('supervisor')
    builder.add_conditional_edges('supervisor', _make_router(resolved_max))
    builder.add_edge('tool_executor', 'supervisor')
    builder.add_edge('verifier', END)

    return builder.compile()
