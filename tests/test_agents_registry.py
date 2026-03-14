from __future__ import annotations

import pytest

from agents.base import AgentDefinition
from agents.editor import EDITOR_AGENT
from agents.planner import PLANNER_AGENT
from agents.searcher import SEARCHER_AGENT
from agents.supervisor import SUPERVISOR_AGENT
from agents.verifier import VERIFIER_AGENT
from core.registry import AGENT_NAMES


# ── Registry ──────────────────────────────────────────────────────────────── #

def test_agent_registry_exposes_expected_agent_names() -> None:
    assert AGENT_NAMES == ('supervisor', 'planner', 'editor', 'verifier', 'searcher')


# ── AgentDefinition dataclass ─────────────────────────────────────────────── #

def test_agent_definition_stores_name_and_description() -> None:
    agent = AgentDefinition(name='test', description='A test agent.')
    assert agent.name == 'test'
    assert agent.description == 'A test agent.'


# ── Individual agent definitions ──────────────────────────────────────────── #

@pytest.mark.parametrize('agent, expected_name', [
    (SUPERVISOR_AGENT, 'supervisor'),
    (PLANNER_AGENT, 'planner'),
    (EDITOR_AGENT, 'editor'),
    (VERIFIER_AGENT, 'verifier'),
    (SEARCHER_AGENT, 'searcher'),
])
def test_agent_definition_name(agent: AgentDefinition, expected_name: str) -> None:
    assert agent.name == expected_name


@pytest.mark.parametrize('agent', [
    SUPERVISOR_AGENT, PLANNER_AGENT, EDITOR_AGENT, VERIFIER_AGENT, SEARCHER_AGENT,
])
def test_agent_definition_has_non_empty_description(agent: AgentDefinition) -> None:
    assert agent.description, f"{agent.name} must have a non-empty description"
