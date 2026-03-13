"""Wrapper for gitleaks secret scanning.

Runs gitleaks if it is installed; skips gracefully if not found.
Install: https://github.com/gitleaks/gitleaks#installing
"""
from __future__ import annotations

import shutil
import subprocess
import sys


def main() -> int:
    if shutil.which("gitleaks") is None:
        print(
            "gitleaks not found — skipping secret scan. "
            "Install it: https://github.com/gitleaks/gitleaks#installing",
            file=sys.stderr,
        )
        return 0

    result = subprocess.run(
        ["gitleaks", "detect", "--no-banner", "--redact", "--source", "."],
        capture_output=False,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
