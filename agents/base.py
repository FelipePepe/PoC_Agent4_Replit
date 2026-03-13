from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class AgentDefinition:
    name: str
    description: str
