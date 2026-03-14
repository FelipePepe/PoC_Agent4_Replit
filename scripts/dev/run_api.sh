#!/usr/bin/env bash
# run_api.sh — Start the PoC Agent4 FastAPI backend with uvicorn
#
# Usage:
#   bash scripts/dev/run_api.sh              # defaults: 127.0.0.1:8000, reload on
#   HOST=0.0.0.0 PORT=8080 bash scripts/dev/run_api.sh
#   RELOAD=false bash scripts/dev/run_api.sh # disable hot-reload (production-like)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"
VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"

# ── Config (overridable via env vars) ─────────────────────────────────────── #
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
RELOAD="${RELOAD:-true}"
LOG_LEVEL="${LOG_LEVEL:-info}"

# ── Load .env if present ──────────────────────────────────────────────────── #
if [ -f "$ENV_FILE" ]; then
    set -o allexport
    # shellcheck source=/dev/null
    source "$ENV_FILE"
    set +o allexport
fi

# ── Select Python interpreter ─────────────────────────────────────────────── #
if [ -f "$VENV_PYTHON" ]; then
    PYTHON="$VENV_PYTHON"
elif command -v python3 &>/dev/null; then
    PYTHON="$(command -v python3)"
else
    echo "ERROR: No Python interpreter found. Activate the venv or install Python 3." >&2
    exit 1
fi

# ── Build uvicorn flags ───────────────────────────────────────────────────── #
UVICORN_ARGS=(
    "core.api:create_app"
    "--factory"
    "--host" "$HOST"
    "--port" "$PORT"
    "--log-level" "$LOG_LEVEL"
)

if [ "$RELOAD" = "true" ]; then
    UVICORN_ARGS+=("--reload")
fi

# ── Launch ────────────────────────────────────────────────────────────────── #
echo "Starting API → http://${HOST}:${PORT}  (reload=${RELOAD}, log=${LOG_LEVEL})"
echo "Docs          → http://${HOST}:${PORT}/docs"
echo "Press Ctrl+C to stop."
echo ""

cd "$PROJECT_ROOT"
exec "$PYTHON" -m uvicorn "${UVICORN_ARGS[@]}"
