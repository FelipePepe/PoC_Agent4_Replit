"""Wrapper for local SonarQube analysis via Docker.

Runs sonar-scanner-cli (Docker) on pre-push if:
  - Docker is installed and running.
  - SONAR_TOKEN is set (env var or .env file).

Skips gracefully if either condition is not met.
Set SONAR_TOKEN in your .env file or export it before pushing.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


def _load_token_from_env_file() -> str:
    env_file = Path(".env")
    if not env_file.exists():
        return ""
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if line.startswith("SONAR_TOKEN="):
            return line.removeprefix("SONAR_TOKEN=").strip().strip("'\"")
    return ""


def main() -> int:
    # ── Check Docker availability ─────────────────────────────────────────── #
    if shutil.which("docker") is None:
        print(
            "docker not found — skipping SonarQube analysis.",
            file=sys.stderr,
        )
        return 0

    # ── Resolve SONAR_TOKEN ───────────────────────────────────────────────── #
    token = os.environ.get("SONAR_TOKEN", "") or _load_token_from_env_file()
    if not token:
        print(
            "[sonar] SONAR_TOKEN not set — skipping analysis.\n"
            "  To enable: add SONAR_TOKEN=<token> to .env or export it.",
            file=sys.stderr,
        )
        return 0

    # ── Delegate to run_sonar.sh ──────────────────────────────────────────── #
    env = {**os.environ, "SONAR_TOKEN": token}
    result = subprocess.run(
        ["bash", "scripts/dev/run_sonar.sh"],
        env=env,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
