"""Sandboxed tools for Fase 1 — read_file, write_file, execute_shell, search_web.

Security model:
- All file operations are confined to AppConfig.workspace_dir (resolved, no escape).
- Shell commands are restricted to AppConfig.allowed_shell_commands (first token check).
- Shell runs without shell=True; shlex.split prevents injection.
- Hard timeout enforced on every shell call.
- search_web is a mock in this phase; import is isolated so it can be swapped later.
"""
from __future__ import annotations

import logging
import shlex
import subprocess
from pathlib import Path
from typing import Any

from langchain_core.tools import tool as lc_tool

from core.config import AppConfig

logger = logging.getLogger(__name__)


# ── Custom exceptions ──────────────────────────────────────────────────────── #


class PathEscapeError(PermissionError):
    """Raised when a path resolves outside the permitted sandbox directory."""


class CommandNotAllowedError(PermissionError):
    """Raised when a shell command is not in the configured allowlist."""


class ShellTimeoutError(TimeoutError):
    """Raised when a shell command exceeds the configured timeout."""


# ── Internal helpers ───────────────────────────────────────────────────────── #


def _resolve_sandbox_path(path: str | Path, config: AppConfig) -> Path:
    """Resolve *path* relative to sandbox and reject escapes.

    Absolute paths outside the sandbox are also rejected.
    """
    sandbox = config.workspace_dir.resolve()
    candidate = Path(path)
    if candidate.is_absolute():
        resolved = candidate.resolve()
    else:
        resolved = (sandbox / candidate).resolve()

    try:
        resolved.relative_to(sandbox)
    except ValueError:
        raise PathEscapeError(
            f'Path {path!r} resolves outside sandbox {sandbox}'
        )
    return resolved


# ── Pure tool implementations ──────────────────────────────────────────────── #


def read_file(path: str | Path, config: AppConfig) -> str:
    """Read a file from the agent sandbox and return its content."""
    resolved = _resolve_sandbox_path(path, config)
    if not resolved.exists():
        raise FileNotFoundError(f'File not found in sandbox: {path!r}')
    content = resolved.read_text(encoding='utf-8')
    logger.info('read_file path=%s bytes=%d', resolved, len(content))
    return content


def write_file(path: str | Path, content: str, config: AppConfig) -> None:
    """Write *content* to a file in the agent sandbox.

    Parent directories are created automatically.
    """
    resolved = _resolve_sandbox_path(path, config)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(content, encoding='utf-8')
    logger.info('write_file path=%s bytes=%d', resolved, len(content))


def execute_shell(command: str, config: AppConfig) -> tuple[int, str, str]:
    """Execute *command* in the sandbox with strict security controls.

    Returns:
        (returncode, stdout, stderr)

    Raises:
        CommandNotAllowedError: first token not in allowed_shell_commands.
        ShellTimeoutError: command exceeded shell_timeout_seconds.
    """
    if not command or not command.strip():
        raise CommandNotAllowedError('Empty command is not allowed')

    try:
        args = shlex.split(command)
    except ValueError as exc:
        raise CommandNotAllowedError(f'Invalid command syntax: {exc}') from exc

    # Extract the executable name (ignore directory component)
    executable = Path(args[0]).name
    if executable not in config.allowed_shell_commands:
        raise CommandNotAllowedError(
            f'Command {executable!r} is not in the allowlist '
            f'{config.allowed_shell_commands}'
        )

    sandbox = config.workspace_dir.resolve()
    logger.info(
        'execute_shell cmd=%r cwd=%s timeout=%ds',
        command,
        sandbox,
        config.shell_timeout_seconds,
    )

    try:
        proc = subprocess.run(
            args,
            cwd=sandbox,
            capture_output=True,
            text=True,
            timeout=config.shell_timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        raise ShellTimeoutError(
            f'Command timed out after {config.shell_timeout_seconds}s: {command!r}'
        ) from exc

    logger.info(
        'execute_shell rc=%d stdout_len=%d stderr_len=%d',
        proc.returncode,
        len(proc.stdout),
        len(proc.stderr),
    )
    return proc.returncode, proc.stdout, proc.stderr


def search_web(query: str) -> str:
    """Search the web for *query*.

    Fase 1: returns a mock response.  Replace with a real implementation in Fase 7+.
    """
    logger.info('search_web query=%r (mock)', query)
    return (
        f'[MOCK SEARCH] Results for "{query}":\n'
        '  - No real search configured in Fase 1.\n'
        '  - Implement a real web search in a later phase.'
    )


# ── LangChain tool wrappers ────────────────────────────────────────────────── #


def make_tools(config: AppConfig) -> list[Any]:
    """Return the four sandboxed LangChain tools bound to *config*."""

    @lc_tool
    def read_file_tool(path: str) -> str:
        """Read a file from the agent sandbox. Returns its text content."""
        try:
            return read_file(path, config)
        except (PathEscapeError, FileNotFoundError) as exc:
            return f'ERROR: {exc}'

    @lc_tool
    def write_file_tool(path: str, content: str) -> str:
        """Write content to a file in the agent sandbox. Creates parent dirs."""
        try:
            write_file(path, content, config)
            return f'OK: wrote {len(content)} bytes to {path!r}'
        except PathEscapeError as exc:
            return f'ERROR: {exc}'

    @lc_tool
    def execute_shell_tool(command: str) -> str:
        """Execute a shell command in the sandbox. Returns stdout or error."""
        try:
            rc, stdout, stderr = execute_shell(command, config)
            if rc == 0:
                return stdout or '(no output)'
            return f'ERROR (rc={rc}): {stderr or stdout}'
        except (CommandNotAllowedError, ShellTimeoutError) as exc:
            return f'ERROR: {exc}'

    @lc_tool
    def search_web_tool(query: str) -> str:
        """Search the web for information about a query."""
        return search_web(query)

    # Rename tools so names match what tests expect
    read_file_tool.name = 'read_file'
    write_file_tool.name = 'write_file'
    execute_shell_tool.name = 'execute_shell'
    search_web_tool.name = 'search_web'

    return [read_file_tool, write_file_tool, execute_shell_tool, search_web_tool]
