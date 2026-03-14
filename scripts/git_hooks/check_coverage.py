"""Pre-commit hook: block commits when test coverage drops below 99%.

Runs the full test suite with pytest-cov and fails if the total branch
coverage is below the required threshold.  The coverage.xml report is
regenerated so that subsequent SonarQube analysis always uses fresh data.

Exit codes:
    0  All tests pass AND coverage >= 99 %.
    1  Tests failed or coverage is below threshold.
"""
from __future__ import annotations

import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

COVERAGE_THRESHOLD = 99
COVERAGE_XML = Path("coverage.xml")
PYTHON = Path(".venv/bin/python")


def _run_tests() -> int:
    """Execute the test suite with coverage reporting.  Returns pytest exit code."""
    result = subprocess.run(
        [
            str(PYTHON),
            "-m", "pytest",
            "--override-ini=addopts=",   # clear pyproject.toml addopts
            "-q",
            "--no-header",
            "--cov=.",
            "--cov-branch",
            "--cov-report=term-missing",
            f"--cov-report=xml:{COVERAGE_XML}",
            f"--cov-fail-under={COVERAGE_THRESHOLD}",
            "tests/",
        ],
    )
    return result.returncode


def _parse_coverage_xml() -> float | None:
    """Return the total line-rate from coverage.xml as a percentage (0–100)."""
    if not COVERAGE_XML.exists():
        return None
    try:
        tree = ET.parse(COVERAGE_XML)  # NOSONAR — parsing a local project file, not user input
        root = tree.getroot()
        line_rate = float(root.attrib.get("line-rate", "0"))
        return round(line_rate * 100, 2)
    except (ET.ParseError, ValueError, KeyError):
        return None


def main() -> int:
    print("[coverage] Running test suite…")
    exit_code = _run_tests()

    coverage = _parse_coverage_xml()
    if coverage is not None:
        symbol = "✔" if coverage >= COVERAGE_THRESHOLD else "✘"
        print(
            f"[coverage] {symbol} Total coverage: {coverage:.2f}% "
            f"(required ≥ {COVERAGE_THRESHOLD}%)"
        )

    if exit_code != 0:
        print(
            f"[coverage] ✘ Commit blocked: tests failed or coverage < {COVERAGE_THRESHOLD}%.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
