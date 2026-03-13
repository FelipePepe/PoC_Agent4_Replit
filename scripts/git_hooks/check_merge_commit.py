from __future__ import annotations

import subprocess
import sys


PROTECTED_BRANCHES = {"main", "develop"}


def current_branch() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def head_parent_count() -> int:
    result = subprocess.run(
        ["git", "rev-list", "--parents", "-n", "1", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return max(len(result.stdout.strip().split()) - 1, 0)


def main() -> int:
    branch = current_branch()
    if branch in PROTECTED_BRANCHES and head_parent_count() > 1:
        print(
            f"Merge commits are blocked on protected branch '{branch}'. Use PR flow.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
