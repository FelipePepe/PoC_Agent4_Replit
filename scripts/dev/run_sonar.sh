#!/usr/bin/env bash
# run_sonar.sh — Run SonarQube analysis via Docker (sonarsource/sonar-scanner-cli)
#
# Usage:
#   SONAR_TOKEN=<your-token> bash scripts/dev/run_sonar.sh
#   # or add SONAR_TOKEN to .env and just run:
#   bash scripts/dev/run_sonar.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"

# ── Load SONAR_TOKEN from .env if not already set ──────────────────────────── #
if [ -z "${SONAR_TOKEN:-}" ] && [ -f "$ENV_FILE" ]; then
    _token_line=$(grep -E '^SONAR_TOKEN=' "$ENV_FILE" 2>/dev/null || true)
    if [ -n "$_token_line" ]; then
        SONAR_TOKEN="${_token_line#SONAR_TOKEN=}"
        SONAR_TOKEN="${SONAR_TOKEN%\"}"
        SONAR_TOKEN="${SONAR_TOKEN#\"}"
        SONAR_TOKEN="${SONAR_TOKEN%\'}"
        SONAR_TOKEN="${SONAR_TOKEN#\'}"
    fi
fi

# ── Validate token ─────────────────────────────────────────────────────────── #
if [ -z "${SONAR_TOKEN:-}" ]; then
    echo "ERROR: SONAR_TOKEN is not set." >&2
    echo "  Export it:  export SONAR_TOKEN=<your-token>" >&2
    echo "  Or add to:  .env  (SONAR_TOKEN=<your-token>)" >&2
    exit 1
fi

# ── Generate coverage report for SonarQube ────────────────────────────────── #
# ── Resolve Python from venv or PATH ──────────────────────────────────────── #
PYTHON_BIN=""
if [ -f "$PROJECT_ROOT/.venv/bin/python" ]; then
    PYTHON_BIN="$PROJECT_ROOT/.venv/bin/python"
elif command -v python3 &>/dev/null; then
    PYTHON_BIN="python3"
elif command -v python &>/dev/null; then
    PYTHON_BIN="python"
fi

# ── Generate coverage report for SonarQube ────────────────────────────────── #
echo "Generating coverage report (coverage.xml)..."
if [ -n "$PYTHON_BIN" ]; then
    # pyproject.toml addopts already includes --cov=. --cov-report=xml:coverage.xml
    (cd "$PROJECT_ROOT" && "$PYTHON_BIN" -m pytest tests/ -q --no-header 2>&1) || {
        echo "WARNING: tests failed or coverage report could not be generated" >&2
    }
    if [ ! -f "$PROJECT_ROOT/coverage.xml" ]; then
        echo "WARNING: coverage.xml not found after test run" >&2
    fi
else
    echo "WARNING: no Python interpreter found; skipping coverage generation" >&2
fi

# ── Run sonar-scanner via Docker ───────────────────────────────────────────── #
echo "Running SonarQube analysis for project: poc-agent4-replit"
docker run --rm \
    --network host \
    -v "$PROJECT_ROOT:/usr/src" \
    -e SONAR_TOKEN="$SONAR_TOKEN" \
    sonarsource/sonar-scanner-cli \
    -Dsonar.token="$SONAR_TOKEN"

echo "Analysis complete. Results at http://localhost:9000/dashboard?id=poc-agent4-replit"
