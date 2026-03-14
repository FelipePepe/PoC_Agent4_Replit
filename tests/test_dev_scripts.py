from __future__ import annotations

from pathlib import Path


VENV_SCRIPT = Path('scripts/dev/enter_venv.sh')
SONAR_SCRIPT = Path('scripts/dev/run_sonar.sh')
SONAR_PROPS = Path('sonar-project.properties')


def test_enter_venv_script_exists() -> None:
    assert VENV_SCRIPT.exists()


def test_enter_venv_script_is_sourceable_and_targets_dot_venv() -> None:
    content = VENV_SCRIPT.read_text(encoding='utf-8')

    assert 'VENV_DIR="${VENV_DIR:-.venv}"' in content
    assert 'source "$VENV_DIR/bin/activate"' in content
    assert 'Run this script with: source scripts/dev/enter_venv.sh' in content


# --- sonar-project.properties ---

def test_sonar_properties_exists() -> None:
    assert SONAR_PROPS.exists(), "sonar-project.properties must exist at project root"


def test_sonar_properties_project_key() -> None:
    content = SONAR_PROPS.read_text(encoding='utf-8')
    assert 'sonar.projectKey=poc-agent4-replit' in content


def test_sonar_properties_sources_and_tests() -> None:
    content = SONAR_PROPS.read_text(encoding='utf-8')
    assert 'sonar.sources=' in content
    assert 'sonar.tests=' in content


def test_sonar_properties_no_token() -> None:
    """Token must never be stored in the properties file (security)."""
    content = SONAR_PROPS.read_text(encoding='utf-8')
    assert 'sonar.token=' not in content
    assert 'sonar.login=squ_' not in content


# --- scripts/dev/run_sonar.sh ---

def test_run_sonar_script_exists() -> None:
    assert SONAR_SCRIPT.exists(), "scripts/dev/run_sonar.sh must exist"


def test_run_sonar_script_is_executable() -> None:
    import stat
    mode = SONAR_SCRIPT.stat().st_mode
    assert mode & stat.S_IXUSR, "run_sonar.sh must be executable"


def test_run_sonar_script_uses_docker() -> None:
    content = SONAR_SCRIPT.read_text(encoding='utf-8')
    assert 'sonarsource/sonar-scanner-cli' in content


def test_run_sonar_script_reads_token_from_env() -> None:
    content = SONAR_SCRIPT.read_text(encoding='utf-8')
    assert 'SONAR_TOKEN' in content
    # Token must not be hardcoded as a real value (starts with squ_ outside of comments)
    import re
    non_comment_lines = [l for l in content.splitlines() if not l.strip().startswith('#')]
    assert all('squ_' not in line for line in non_comment_lines), \
        "Hardcoded token detected in a non-comment line of run_sonar.sh"


def test_run_sonar_script_fails_without_token() -> None:
    """Script must exit with error if SONAR_TOKEN is empty."""
    content = SONAR_SCRIPT.read_text(encoding='utf-8')
    assert 'SONAR_TOKEN' in content
    assert 'exit 1' in content or 'exit 2' in content
