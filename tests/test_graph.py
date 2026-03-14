"""Tests for core/graph.py — minimal LangGraph graph (Fase 0 exit criterion).

Uses a mock LLM so tests run without an ANTHROPIC_API_KEY.
The graph must:
  - Accept a human message as input
  - Pass it through a single 'supervisor' node
  - Return an AIMessage in state['messages']
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from core.graph import GraphConfig, build_graph
from core.state import AgentState, create_initial_state


class TestBuildGraph:
    def test_returns_compiled_graph(self):
        graph = build_graph()
        # CompiledGraph has an invoke method
        assert callable(getattr(graph, 'invoke', None))

    def test_graph_has_supervisor_node(self):
        graph = build_graph()
        nodes = set(graph.get_graph().nodes.keys())
        assert 'supervisor' in nodes

    def test_graph_config_default_model(self):
        cfg = GraphConfig()
        assert cfg.model_name == 'claude-sonnet-4-5'

    def test_graph_config_custom_model(self):
        cfg = GraphConfig(model_name='claude-haiku-3-5')
        assert cfg.model_name == 'claude-haiku-3-5'


class TestGraphInvoke:
    """Integration-style tests using a patched LLM — no real API calls."""

    def _make_mock_llm(self, reply: str = 'mocked reply') -> MagicMock:
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = AIMessage(content=reply)
        return mock_llm

    def test_invoke_returns_ai_message(self):
        mock_llm = self._make_mock_llm('Hello from mock')
        with patch('core.graph.build_llm', return_value=mock_llm):
            graph = build_graph()
            initial = create_initial_state(task_id='t1')
            initial['messages'] = [HumanMessage(content='Say hello')]
            result = graph.invoke(initial)
        messages = result['messages']
        ai_messages = [m for m in messages if isinstance(m, AIMessage)]
        assert len(ai_messages) >= 1
        assert ai_messages[-1].content == 'Hello from mock'

    def test_invoke_preserves_task_id(self):
        mock_llm = self._make_mock_llm()
        with patch('core.graph.build_llm', return_value=mock_llm):
            graph = build_graph()
            initial = create_initial_state(task_id='task-abc')
            initial['messages'] = [HumanMessage(content='test')]
            result = graph.invoke(initial)
        assert result['task_id'] == 'task-abc'

    def test_invoke_sets_active_agent_to_supervisor(self):
        mock_llm = self._make_mock_llm()
        with patch('core.graph.build_llm', return_value=mock_llm):
            graph = build_graph()
            initial = create_initial_state(task_id='t2')
            initial['messages'] = [HumanMessage(content='test')]
            result = graph.invoke(initial)
        assert result['active_agent'] == 'supervisor'

    def test_llm_receives_messages(self):
        mock_llm = self._make_mock_llm()
        with patch('core.graph.build_llm', return_value=mock_llm):
            graph = build_graph()
            initial = create_initial_state(task_id='t3')
            initial['messages'] = [HumanMessage(content='ping')]
            graph.invoke(initial)
        mock_llm.invoke.assert_called_once()
