#!/usr/bin/env bash

# Run this script with: source scripts/dev/enter_venv.sh
# Optional override: VENV_DIR=/path/to/venv source scripts/dev/enter_venv.sh

VENV_DIR="${VENV_DIR:-.venv}"

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  echo "Run this script with: source scripts/dev/enter_venv.sh" >&2
  exit 1
fi

if [[ ! -f "$VENV_DIR/bin/activate" ]]; then
  echo "Virtual environment not found at '$VENV_DIR'." >&2
  return 1
fi

source "$VENV_DIR/bin/activate"
