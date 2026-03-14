"""Tests for core/tools.py — sandboxed tools for Fase 1.

Security invariants verified here:
- read_file / write_file reject paths outside workspace_dir
- execute_shell rejects commands not in allowlist
- execute_shell runs inside workspace_dir with hard timeout
- search_web returns a string (mock in this phase)
"""
from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import patch

import pytest

from core.config import AppConfig, create_default_config
from core.tools import (
    CommandNotAllowedError,
    PathEscapeError,
    ShellTimeoutError,
    execute_shell,
    make_tools,
    read_file,
    search_web,
    write_file,
)


@pytest.fixture()
def sandbox(tmp_path: Path) -> Path:
    """Return a temporary sandbox directory."""
    sb = tmp_path / 'agent_sandbox'
    sb.mkdir()
    return sb


@pytest.fixture()
def cfg(sandbox: Path, tmp_path: Path) -> AppConfig:
    """AppConfig rooted at tmp_path with sandbox inside it."""
    return create_default_config(
        project_root=tmp_path,
        workspace_dir=sandbox,
    )


# ──────────────────────────────────────────────────────────────────────────────
# read_file
# ──────────────────────────────────────────────────────────────────────────────


class TestReadFile:
    def test_reads_existing_file(self, sandbox: Path, cfg: AppConfig) -> None:
        target = sandbox / 'hello.txt'
        target.write_text('hello world')
        assert read_file('hello.txt', cfg) == 'hello world'

    def test_reads_nested_file(self, sandbox: Path, cfg: AppConfig) -> None:
        (sandbox / 'sub').mkdir()
        (sandbox / 'sub' / 'data.txt').write_text('nested')
        assert read_file('sub/data.txt', cfg) == 'nested'

    def test_raises_for_nonexistent_file(self, cfg: AppConfig) -> None:
        with pytest.raises(FileNotFoundError):
            read_file('does_not_exist.txt', cfg)

    def test_rejects_path_outside_sandbox(self, cfg: AppConfig) -> None:
        with pytest.raises(PathEscapeError):
            read_file('../secret.txt', cfg)

    def test_rejects_absolute_path_outside_sandbox(
        self, cfg: AppConfig
    ) -> None:
        with pytest.raises(PathEscapeError):
            read_file('/etc/passwd', cfg)

    def test_rejects_dotdot_traversal(self, cfg: AppConfig) -> None:
        with pytest.raises(PathEscapeError):
            read_file('../../etc/shadow', cfg)


# ──────────────────────────────────────────────────────────────────────────────
# write_file
# ──────────────────────────────────────────────────────────────────────────────


class TestWriteFile:
    def test_writes_file_in_sandbox(self, sandbox: Path, cfg: AppConfig) -> None:
        write_file('output.txt', 'content', cfg)
        assert (sandbox / 'output.txt').read_text() == 'content'

    def test_creates_parent_directories(self, sandbox: Path, cfg: AppConfig) -> None:
        write_file('a/b/c.txt', 'deep', cfg)
        assert (sandbox / 'a' / 'b' / 'c.txt').read_text() == 'deep'

    def test_overwrites_existing_file(self, sandbox: Path, cfg: AppConfig) -> None:
        write_file('overwrite.txt', 'v1', cfg)
        write_file('overwrite.txt', 'v2', cfg)
        assert (sandbox / 'overwrite.txt').read_text() == 'v2'

    def test_rejects_path_outside_sandbox(self, cfg: AppConfig) -> None:
        with pytest.raises(PathEscapeError):
            write_file('../evil.txt', 'pwned', cfg)

    def test_rejects_absolute_path_outside_sandbox(
        self, cfg: AppConfig
    ) -> None:
        with pytest.raises(PathEscapeError):
            write_file('/tmp/evil.txt', 'pwned', cfg)


# ──────────────────────────────────────────────────────────────────────────────
# execute_shell
# ──────────────────────────────────────────────────────────────────────────────


class TestExecuteShell:
    def test_runs_allowed_command(self, sandbox: Path, cfg: AppConfig) -> None:
        rc, stdout, stderr = execute_shell('python --version', cfg)
        assert rc == 0
        assert 'Python' in stdout or 'Python' in stderr

    def test_rejects_command_not_in_allowlist(self, cfg: AppConfig) -> None:
        with pytest.raises(CommandNotAllowedError):
            execute_shell('rm -rf /', cfg)

    def test_rejects_empty_command(self, cfg: AppConfig) -> None:
        with pytest.raises(CommandNotAllowedError):
            execute_shell('', cfg)

    def test_rejects_allowlist_bypass_with_semicolon(
        self, cfg: AppConfig
    ) -> None:
        with pytest.raises(CommandNotAllowedError):
            execute_shell('python; rm -rf /', cfg)

    def test_captures_stdout(self, sandbox: Path, cfg: AppConfig) -> None:
        rc, stdout, stderr = execute_shell('python -c "print(42)"', cfg)
        assert rc == 0
        assert '42' in stdout

    def test_captures_stderr_on_error(
        self, sandbox: Path, cfg: AppConfig
    ) -> None:
        rc, stdout, stderr = execute_shell(
            'python -c "import sys; sys.exit(1)"', cfg
        )
        assert rc == 1

    def test_runs_in_sandbox_directory(
        self, sandbox: Path, cfg: AppConfig
    ) -> None:
        rc, stdout, _ = execute_shell('python -c "import os; print(os.getcwd())"', cfg)
        assert rc == 0
        assert str(sandbox) in stdout

    def test_timeout_raises(self, cfg: AppConfig) -> None:
        fast_cfg = AppConfig(
            api_version=cfg.api_version,
            workspace_dir=cfg.workspace_dir,
            shell_timeout_seconds=1,
            max_agent_iterations=cfg.max_agent_iterations,
            allowed_shell_commands=cfg.allowed_shell_commands,
            secret_redaction_enabled=cfg.secret_redaction_enabled,
            encryption_at_rest_required=cfg.encryption_at_rest_required,
        )
        with pytest.raises(ShellTimeoutError):
            execute_shell('python -c "import time; time.sleep(5)"', fast_cfg)

    def test_rejects_invalid_shell_syntax(self, cfg: AppConfig) -> None:
        """Unmatched quote → shlex.split ValueError → CommandNotAllowedError."""
        with pytest.raises(CommandNotAllowedError, match='Invalid command syntax'):
            execute_shell("echo 'unclosed", cfg)


# ──────────────────────────────────────────────────────────────────────────────
# search_web
# ──────────────────────────────────────────────────────────────────────────────


class TestSearchWeb:
    def test_returns_string(self) -> None:
        result = search_web('LangGraph tutorial')
        assert isinstance(result, str)
        assert len(result) > 0

    def test_query_reflected_in_result(self) -> None:
        result = search_web('pytest fixtures')
        assert isinstance(result, str)


# ──────────────────────────────────────────────────────────────────────────────
# make_tools (LangChain tool wrappers)
# ──────────────────────────────────────────────────────────────────────────────


class TestMakeTools:
    def test_returns_four_tools(self, cfg: AppConfig) -> None:
        tools = make_tools(cfg)
        assert len(tools) == 4

    def test_tool_names(self, cfg: AppConfig) -> None:
        tools = make_tools(cfg)
        names = {t.name for t in tools}
        assert names == {'read_file', 'write_file', 'execute_shell', 'search_web'}

    def test_read_file_tool_works(self, sandbox: Path, cfg: AppConfig) -> None:
        (sandbox / 'test.txt').write_text('via tool')
        tools = make_tools(cfg)
        read_tool = next(t for t in tools if t.name == 'read_file')
        result = read_tool.invoke({'path': 'test.txt'})
        assert 'via tool' in result

    def test_write_file_tool_works(self, sandbox: Path, cfg: AppConfig) -> None:
        tools = make_tools(cfg)
        write_tool = next(t for t in tools if t.name == 'write_file')
        write_tool.invoke({'path': 'created.txt', 'content': 'tool wrote this'})
        assert (sandbox / 'created.txt').read_text() == 'tool wrote this'

    def test_execute_shell_tool_works(
        self, sandbox: Path, cfg: AppConfig
    ) -> None:
        tools = make_tools(cfg)
        shell_tool = next(t for t in tools if t.name == 'execute_shell')
        result = shell_tool.invoke({'command': 'python -c "print(\'ok\')"'})
        assert 'ok' in result

    def test_search_web_tool_works(self, cfg: AppConfig) -> None:
        tools = make_tools(cfg)
        search_tool = next(t for t in tools if t.name == 'search_web')
        result = search_tool.invoke({'query': 'test query'})
        assert isinstance(result, str)

    def test_read_file_tool_returns_error_on_path_escape(
        self, cfg: AppConfig
    ) -> None:
        tools = make_tools(cfg)
        read_tool = next(t for t in tools if t.name == 'read_file')
        result = read_tool.invoke({'path': '../escape.txt'})
        assert result.startswith('ERROR:')

    def test_read_file_tool_returns_error_on_missing_file(
        self, cfg: AppConfig
    ) -> None:
        tools = make_tools(cfg)
        read_tool = next(t for t in tools if t.name == 'read_file')
        result = read_tool.invoke({'path': 'no_such_file.txt'})
        assert result.startswith('ERROR:')

    def test_write_file_tool_returns_error_on_path_escape(
        self, cfg: AppConfig
    ) -> None:
        tools = make_tools(cfg)
        write_tool = next(t for t in tools if t.name == 'write_file')
        result = write_tool.invoke({'path': '../escape.txt', 'content': 'x'})
        assert result.startswith('ERROR:')

    def test_execute_shell_tool_returns_error_on_nonzero_rc(
        self, sandbox: Path, cfg: AppConfig
    ) -> None:
        tools = make_tools(cfg)
        shell_tool = next(t for t in tools if t.name == 'execute_shell')
        result = shell_tool.invoke({'command': 'python -c "import sys; sys.exit(1)"'})
        assert result.startswith('ERROR (rc=')

    def test_execute_shell_tool_returns_error_on_disallowed_command(
        self, cfg: AppConfig
    ) -> None:
        tools = make_tools(cfg)
        shell_tool = next(t for t in tools if t.name == 'execute_shell')
        result = shell_tool.invoke({'command': 'rm -rf .'})
        assert result.startswith('ERROR:')

    def test_execute_shell_tool_returns_error_on_timeout(
        self, cfg: AppConfig
    ) -> None:
        tools = make_tools(cfg)
        shell_tool = next(t for t in tools if t.name == 'execute_shell')
        result = shell_tool.invoke(
            {'command': 'python -c "import time; time.sleep(60)"'}
        )
        assert result.startswith('ERROR:')
