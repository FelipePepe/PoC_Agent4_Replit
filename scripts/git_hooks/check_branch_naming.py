from __future__ import annotations

import re
import subprocess
import sys


ALLOWED_PATTERNS = (
    r"main",
    r"develop",
    r"feature/[a-z0-9._-]+",
    r"bugfix/[a-z0-9._-]+",
    r"chore/[a-z0-9._-]+",
    r"docs/[a-z0-9._-]+",
    r"refactor/[a-z0-9._-]+",
    r"release/[a-z0-9._-]+",
    r"hotfix/[a-z0-9._-]+",
    r"spike/[a-z0-9._-]+",
)


def _has_commits() -> bool:
    """Return True if the repository has at least one commit."""
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD"],
        capture_output=True,
    )
    return result.returncode == 0


def current_branch() -> str | None:
    """Return the current branch name, or None when HEAD is unborn (no commits yet)."""
    result = subprocess.run(
        ["git", "symbolic-ref", "--short", "HEAD"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def main() -> int:
    if not _has_commits():
        # Unborn branch (first commit) — skip naming check.
        return 0
    branch = current_branch()
    if branch is None:
        # Detached HEAD — skip naming check.
        return 0
    if any(re.fullmatch(pattern, branch) for pattern in ALLOWED_PATTERNS):
        return 0

    print(
        "Invalid branch name. Use one of: main, develop, feature/*, bugfix/*, "
        "chore/*, docs/*, refactor/*, release/*, hotfix/*, spike/*.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
