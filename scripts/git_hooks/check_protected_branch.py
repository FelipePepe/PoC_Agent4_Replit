from __future__ import annotations

import subprocess
import sys


PROTECTED_BRANCHES = {"main", "develop"}


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
        # Detached HEAD — cannot determine branch name.
        return None
    return result.stdout.strip()


def main() -> int:
    if not _has_commits():
        # Unborn branch (first commit in a new repo) — allow unconditionally.
        return 0
    branch = current_branch()
    if branch is None:
        return 0
    if branch in PROTECTED_BRANCHES:
        print(
            f"Direct commits are blocked on protected branch '{branch}'. Use a PR.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
