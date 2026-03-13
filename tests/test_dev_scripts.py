from __future__ import annotations

from pathlib import Path


SCRIPT_PATH = Path('scripts/dev/enter_venv.sh')


def test_enter_venv_script_exists() -> None:
    assert SCRIPT_PATH.exists()



def test_enter_venv_script_is_sourceable_and_targets_dot_venv() -> None:
    content = SCRIPT_PATH.read_text(encoding='utf-8')

    assert 'VENV_DIR="${VENV_DIR:-.venv}"' in content
    assert 'source "$VENV_DIR/bin/activate"' in content
    assert 'Run this script with: source scripts/dev/enter_venv.sh' in content
