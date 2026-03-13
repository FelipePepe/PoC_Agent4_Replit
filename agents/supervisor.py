from __future__ import annotations

from agents.base import AgentDefinition

SUPERVISOR_AGENT = AgentDefinition(
    name='supervisor',
    description='Coordinates task flow and delegates work to specialized agents.',
)
