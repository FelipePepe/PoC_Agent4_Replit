"""Wrapper for local SonarQube analysis via Docker — runs in the background.

Triggered on post-push so it never blocks the push.  The scanner runs as a
detached background process; its output is written to .sonar_analysis.log in
the project root.

Skips gracefully if:
  - Docker is not installed or not running.
  - SONAR_TOKEN is not set (env var or .env file).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

LOG_FILE = Path(".sonar_analysis.log")


def _load_token_from_env_file() -> str:
    env_file = Path(".env")
    if not env_file.exists():
        return ""
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if line.startswith("SONAR_TOKEN="):
            return line.removeprefix("SONAR_TOKEN=").strip().strip("'\"")
    return ""


def main() -> int:  # NOSONAR — hook always returns 0: non-blocking by design, push must never be blocked
    # ── Check Docker availability ─────────────────────────────────────────── #
    if shutil.which("docker") is None:
        print(
            "[sonar] docker not found — skipping SonarQube analysis.",
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

    # ── Launch scanner in the background (non-blocking) ───────────────────── #
    log_fd = LOG_FILE.open("w", encoding="utf-8")
    env = {**os.environ, "SONAR_TOKEN": token}
    subprocess.Popen(  # NOSONAR — controlled command, allowlisted path
        ["bash", "scripts/dev/run_sonar.sh"],
        env=env,
        stdout=log_fd,
        stderr=log_fd,
        start_new_session=True,   # detach from parent so push is not blocked
    )
    print(
        f"[sonar] SonarQube analysis launched in the background.\n"
        f"  Follow progress: tail -f {LOG_FILE}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
