"""Tests for core/graph.py — minimal LangGraph graph (Fase 0 exit criterion)
and ReAct loop with sandboxed tools (Fase 1).

Uses a mock LLM so tests run without an ANTHROPIC_API_KEY.
The graph must:
  - Accept a human message as input
  - Pass it through a single 'supervisor' node (Fase 0)
  - Return an AIMessage in state['messages']
  - Execute tool calls via 'tool_executor' node (Fase 1)
  - Validate results via 'verifier' node (Fase 1)
  - Respect max_agent_iterations limit (Fase 1)
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

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

    def test_graph_has_tool_executor_node(self):
        graph = build_graph()
        nodes = set(graph.get_graph().nodes.keys())
        assert 'tool_executor' in nodes

    def test_graph_has_verifier_node(self):
        graph = build_graph()
        nodes = set(graph.get_graph().nodes.keys())
        assert 'verifier' in nodes

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
        bound = MagicMock()
        mock_llm.bind_tools.return_value = bound
        bound.invoke.return_value = AIMessage(content=reply)
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

    def test_invoke_active_agent_ends_at_verifier(self):
        """After a full run (no tool calls) the verifier is the final node."""
        mock_llm = self._make_mock_llm()
        with patch('core.graph.build_llm', return_value=mock_llm):
            graph = build_graph()
            initial = create_initial_state(task_id='t2')
            initial['messages'] = [HumanMessage(content='test')]
            result = graph.invoke(initial)
        assert result['active_agent'] == 'verifier'

    def test_llm_receives_messages(self):
        mock_llm = self._make_mock_llm()
        with patch('core.graph.build_llm', return_value=mock_llm):
            graph = build_graph()
            initial = create_initial_state(task_id='t3')
            initial['messages'] = [HumanMessage(content='ping')]
            graph.invoke(initial)
        mock_llm.bind_tools.return_value.invoke.assert_called()


class TestReActLoop:
    """Tests for the Fase 1 ReAct loop: supervisor → tool_executor → supervisor → verifier."""

    def _make_tool_call_message(self, tool_name: str, args: dict, call_id: str = 'call_1') -> AIMessage:
        return AIMessage(
            content='',
            tool_calls=[{
                'name': tool_name,
                'args': args,
                'id': call_id,
                'type': 'tool_call',
            }],
        )

    def test_react_loop_executes_tool_and_terminates(self, tmp_path: Path):
        """Full ReAct round: tool call → tool result → final answer."""
        sandbox = tmp_path / 'agent_sandbox'
        sandbox.mkdir()

        mock_llm = MagicMock()
        bound = MagicMock()
        mock_llm.bind_tools.return_value = bound
        bound.invoke.side_effect = [
            # Round 1: write hello.py
            self._make_tool_call_message(
                'write_file',
                {'path': 'hello.py', 'content': 'print("Hola Mundo")'},
                'call_1',
            ),
            # Round 2: no more tool calls — task done
            AIMessage(content='Created hello.py successfully.'),
        ]

        with patch('core.graph.build_llm', return_value=mock_llm):
            graph = build_graph(app_config_workspace=sandbox)
            initial = create_initial_state(task_id='fase1')
            initial['messages'] = [
                HumanMessage(content='crea un fichero hello.py que imprima Hola Mundo')
            ]
            result = graph.invoke(initial)

        assert (sandbox / 'hello.py').exists()
        assert 'Hola Mundo' in (sandbox / 'hello.py').read_text()
        final_ai = [m for m in result['messages'] if isinstance(m, AIMessage)]
        assert final_ai[-1].content == 'Created hello.py successfully.'

    def test_tool_message_appended_after_tool_call(self, tmp_path: Path):
        """ToolMessage is added to state messages after each tool execution."""
        sandbox = tmp_path / 'agent_sandbox'
        sandbox.mkdir()

        mock_llm = MagicMock()
        bound = MagicMock()
        mock_llm.bind_tools.return_value = bound
        bound.invoke.side_effect = [
            self._make_tool_call_message(
                'write_file', {'path': 'f.txt', 'content': 'x'}, 'cid'
            ),
            AIMessage(content='Done'),
        ]

        with patch('core.graph.build_llm', return_value=mock_llm):
            graph = build_graph(app_config_workspace=sandbox)
            initial = create_initial_state(task_id='t-tool')
            initial['messages'] = [HumanMessage(content='write a file')]
            result = graph.invoke(initial)

        tool_messages = [m for m in result['messages'] if isinstance(m, ToolMessage)]
        assert len(tool_messages) >= 1

    def test_tool_calls_recorded_in_state(self, tmp_path: Path):
        """state['tool_calls'] is populated with executed calls."""
        sandbox = tmp_path / 'agent_sandbox'
        sandbox.mkdir()

        mock_llm = MagicMock()
        bound = MagicMock()
        mock_llm.bind_tools.return_value = bound
        bound.invoke.side_effect = [
            self._make_tool_call_message(
                'write_file', {'path': 'x.txt', 'content': 'y'}, 'cid2'
            ),
            AIMessage(content='done'),
        ]

        with patch('core.graph.build_llm', return_value=mock_llm):
            graph = build_graph(app_config_workspace=sandbox)
            initial = create_initial_state(task_id='t-state')
            initial['messages'] = [HumanMessage(content='task')]
            result = graph.invoke(initial)

        assert isinstance(result['tool_calls'], list)
        assert len(result['tool_calls']) >= 1

    def test_max_iterations_respected(self, tmp_path: Path):
        """Graph stops calling tools after max_agent_iterations rounds."""
        sandbox = tmp_path / 'agent_sandbox'
        sandbox.mkdir()

        mock_llm = MagicMock()
        bound = MagicMock()
        mock_llm.bind_tools.return_value = bound
        # Always return a tool call — graph must enforce the limit itself
        bound.invoke.return_value = self._make_tool_call_message(
            'search_web', {'query': 'loop'}, 'cid3'
        )

        with patch('core.graph.build_llm', return_value=mock_llm):
            # max_agent_iterations=3 to keep test fast
            graph = build_graph(app_config_workspace=sandbox, max_iterations=3)
            initial = create_initial_state(task_id='t-max')
            initial['messages'] = [HumanMessage(content='loop forever')]
            result = graph.invoke(initial)

        # LLM must have been called at most max+1 times (one final pass to check)
        assert bound.invoke.call_count <= 4

    def test_verifier_node_called_at_end(self, tmp_path: Path):
        """Verifier node sets active_agent to 'verifier' in final state."""
        sandbox = tmp_path / 'agent_sandbox'
        sandbox.mkdir()

        mock_llm = MagicMock()
        bound = MagicMock()
        mock_llm.bind_tools.return_value = bound
        bound.invoke.return_value = AIMessage(content='Task complete.')

        with patch('core.graph.build_llm', return_value=mock_llm):
            graph = build_graph(app_config_workspace=sandbox)
            initial = create_initial_state(task_id='t-verify')
            initial['messages'] = [HumanMessage(content='do something')]
            result = graph.invoke(initial)

        assert result['active_agent'] == 'verifier'
