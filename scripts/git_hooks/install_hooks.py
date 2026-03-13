from __future__ import annotations

import subprocess
from pathlib import Path


HOOKS_DIR = Path(".git/hooks")


def write_hook(name: str, command: str) -> None:
    HOOKS_DIR.mkdir(parents=True, exist_ok=True)
    hook_path = HOOKS_DIR / name
    hook_path.write_text(f"#!/usr/bin/env sh\n{command}\n", encoding="utf-8")
    hook_path.chmod(0o755)


def main() -> int:
    subprocess.run(["pre-commit", "install"], check=True)
    subprocess.run(["pre-commit", "install", "--hook-type", "pre-push"], check=True)
    write_hook("commit-msg", "python scripts/git_hooks/validate_commit_msg.py \"$1\"")
    write_hook("pre-merge-commit", "python scripts/git_hooks/check_merge_commit.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
