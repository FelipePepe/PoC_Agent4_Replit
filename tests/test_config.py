from __future__ import annotations

from pathlib import Path

import pytest

from core.config import AppConfig, ConfigValidationError, create_default_config


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_create_default_config_uses_secure_defaults() -> None:
    config = create_default_config(project_root=PROJECT_ROOT)

    assert config.api_version == 'v1'
    assert config.shell_timeout_seconds == 10
    assert config.max_agent_iterations == 10
    assert config.workspace_dir == PROJECT_ROOT / 'workspace' / 'agent_sandbox'
    assert config.allowed_shell_commands == ('python', 'pytest')
    assert config.secret_redaction_enabled is True
    assert config.encryption_at_rest_required is True


@pytest.mark.parametrize(
    ('shell_timeout_seconds', 'max_agent_iterations'),
    [
        (0, 10),
        (-1, 10),
        (10, 0),
    ],
)
def test_config_rejects_non_positive_limits(
    shell_timeout_seconds: int,
    max_agent_iterations: int,
) -> None:
    with pytest.raises(ConfigValidationError):
        AppConfig(
            api_version='v1',
            workspace_dir=PROJECT_ROOT / 'workspace' / 'agent_sandbox',
            shell_timeout_seconds=shell_timeout_seconds,
            max_agent_iterations=max_agent_iterations,
            allowed_shell_commands=('python',),
            secret_redaction_enabled=True,
            encryption_at_rest_required=True,
        )


def test_config_rejects_workspace_outside_project_root() -> None:
    with pytest.raises(ConfigValidationError):
        create_default_config(project_root=PROJECT_ROOT, workspace_dir=Path('/tmp/outside'))
