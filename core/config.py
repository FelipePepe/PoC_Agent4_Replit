from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class ConfigValidationError(ValueError):
    """Raised when application configuration is insecure or invalid."""


@dataclass(slots=True, frozen=True)
class AppConfig:
    api_version: str
    workspace_dir: Path
    shell_timeout_seconds: int
    max_agent_iterations: int
    allowed_shell_commands: tuple[str, ...]
    secret_redaction_enabled: bool
    encryption_at_rest_required: bool

    def __post_init__(self) -> None:
        if self.shell_timeout_seconds <= 0:
            raise ConfigValidationError('shell_timeout_seconds must be positive')
        if self.max_agent_iterations <= 0:
            raise ConfigValidationError('max_agent_iterations must be positive')
        if not self.allowed_shell_commands:
            raise ConfigValidationError('allowed_shell_commands must not be empty')


def create_default_config(
    project_root: Path,
    workspace_dir: Path | None = None,
) -> AppConfig:
    resolved_project_root = project_root.resolve()
    resolved_workspace_dir = (
        workspace_dir.resolve()
        if workspace_dir is not None
        else resolved_project_root / 'workspace' / 'agent_sandbox'
    )

    try:
        resolved_workspace_dir.relative_to(resolved_project_root)
    except ValueError as exc:
        raise ConfigValidationError(
            'workspace_dir must remain inside the project root'
        ) from exc

    return AppConfig(
        api_version='v1',
        workspace_dir=resolved_workspace_dir,
        shell_timeout_seconds=10,
        max_agent_iterations=10,
        allowed_shell_commands=('python', 'pytest'),
        secret_redaction_enabled=True,
        encryption_at_rest_required=True,
    )
