from __future__ import annotations

import re
import sys
from pathlib import Path


CONVENTIONAL_COMMIT_RE = re.compile(
    r"^(feat|fix|docs|style|refactor|test|chore|build|ci|perf|revert)"
    r"(\([a-z0-9._/-]+\))?!?: .+"
)


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: validate_commit_msg.py <commit-msg-file>", file=sys.stderr)
        return 1

    commit_msg_path = Path(sys.argv[1])
    first_line = commit_msg_path.read_text(encoding="utf-8").splitlines()[0].strip()

    if CONVENTIONAL_COMMIT_RE.fullmatch(first_line):
        return 0

    print(
        "Invalid commit message. Use Conventional Commits, e.g. "
        "'feat(core): add task state machine'.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
