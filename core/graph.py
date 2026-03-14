"""Minimal LangGraph graph — Fase 0 exit criterion.

Defines a single-node graph with a 'supervisor' node that calls the LLM
and returns the response. No conditional edges — just entry → supervisor → END.

Usage:
    graph = build_graph()
    result = graph.invoke(create_initial_state(task_id="abc"))
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
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


def build_graph(cfg: GraphConfig | None = None):
    """Compile and return the minimal LangGraph graph for Fase 0.

    Graph topology:
        START → supervisor → END
    """
    llm = build_llm(cfg)

    def supervisor_node(state: AgentState) -> dict:
        """Single supervisor node: sends messages to the LLM and appends reply."""
        logger.info(
            'supervisor_node called — task_id=%s messages=%d',
            state.get('task_id', '?'),
            len(state.get('messages', [])),
        )
        response = llm.invoke(state['messages'])
        logger.info('supervisor_node response — content_len=%d', len(str(response.content)))
        return {
            'messages': state['messages'] + [response],
            'active_agent': 'supervisor',
        }

    builder = StateGraph(AgentState)
    builder.add_node('supervisor', supervisor_node)
    builder.set_entry_point('supervisor')
    builder.add_edge('supervisor', END)

    return builder.compile()
