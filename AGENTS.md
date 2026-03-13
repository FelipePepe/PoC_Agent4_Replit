# Repository Guidelines

## Project Structure & Module Organization
This repository is a **spec-first PoC** for a Replit Agent 4–style multi-agent system. The canonical spec is `poc-agent4-prompt-v2.md`; read it before coding.

Expected code layout (as implementation grows):
- `core/` — graph wiring, shared state, model routing, DB setup
- `agents/` — supervisor, planner, editor, verifier, searcher
- `guidance/` — decision-time classifier and micro-instructions
- `snapshots/` — snapshot/rollback engine
- `tests/` — unit and integration tests
- `workspace/agent_sandbox/` — isolated runtime workdir for agent file/shell actions

## Build, Test, and Development Commands
Use Python 3.11+.

- `python -m core.graph` — run the main LangGraph flow
- `python -m pytest tests/` — run test suite
- `python -c "import langgraph; print(langgraph.__version__)"` — verify LangGraph version
- `ollama run phi3-mini "test"` — quick local classifier latency check

Install dependencies (example):
`pip install langgraph>=0.2 langchain-anthropic langsmith anthropic gitpython mcp`

## Coding Style & Naming Conventions
- Follow PEP 8, 4-space indentation, and type hints on public functions.
- Use `snake_case` for modules/functions/variables, `PascalCase` for classes.
- Keep modules focused (one responsibility per file).
- Agent files must stay small and readable: target **<= 200 lines** per file; if a file grows beyond that, split helpers, policies, prompts, and orchestration logic into submodules. Treat **300 lines** as a hard refactor threshold.
- Prefer explicit state keys in `core/state.py`; avoid ad-hoc state mutations.

## Testing Guidelines
- Framework: `pytest`.
- This project follows **strict TDD** as a non-negotiable rule: **red -> green -> refactor**, always writing the test first and the code after.
- Place tests under `tests/` using `test_<module>.py` naming.
- Add integration tests for agent handoffs and tool loops.
- Add regression tests for snapshot restore and model-switch thresholds.

## Commit & Pull Request Guidelines
Git history is not available in this snapshot, so adopt **Conventional Commits**:
- `feat: add planner handoff validation`
- `fix: enforce sandbox command timeout`

Branching model:
- Protected branches: `main`, `develop`
- Delivery branches: `release/*`, `hotfix/*`
- Working branches from `develop`: `feature/*`, `bugfix/*`, `chore/*`, `docs/*`, `refactor/*`
- Optional exploration branch: `spike/*`
- Never commit directly to `main` or `develop`; both must be updated only through Pull Requests.
- `main` accepts PRs only from `release/*` or `hotfix/*`.
- `develop` accepts PRs from `feature/*`, `bugfix/*`, `chore/*`, `docs/*`, `refactor/*`, and `spike/*` when explicitly approved.

PRs should include:
1. Clear summary and scope
2. Linked issue/task (if any)
3. Test evidence (`pytest` output)
4. Logs/screenshots for behavioral changes

Local git controls expected for this repo:
- `pre-commit` for fast checks (format/lint/secret scanning and policy checks)
- `commit-msg` for Conventional Commit validation
- `pre-push` for heavier validation, including tests and local SonarQube analysis when configured
- Hooks must reject commits on `main` and `develop`, and reject local merge commits targeting protected branches

## Security & Configuration Tips
- This project must be implemented with **security first, security by design, and security by default** as non-negotiable principles.
- All implementation and review work should also follow **OWASP Top 10** guidance as a baseline secure-development reference.
- Apply mandatory **secret management**: no plaintext secrets, **encryption at rest** for persisted credentials/tokens, redaction in logs/errors, and backend-only secret access.
- Apply **RBAC** (Role-Based Access Control) and least privilege for any sensitive operation, secret access, or future administrative capability.
- Prefer **deny-by-default** behavior: reject unsupported state transitions, disallow non-allowlisted shell commands, and expose only explicitly defined endpoints/actions.
- Apply **least privilege** everywhere: isolate agent execution to `workspace/agent_sandbox/`, minimize filesystem scope, and keep model/provider credentials backend-only.
- Enforce **strict validation** on inputs, headers, task state transitions, idempotency keys, and event payloads.
- Make secure defaults mandatory: hard timeouts, bounded resource/token usage, structured audit logs, and sanitized error responses without secret leakage.
- Add secret scanning with **Gitleaks** locally and in CI.
- Never commit `.env` or API keys (`ANTHROPIC_API_KEY`, `LANGSMITH_API_KEY`).
- Restrict shell execution to allowlisted commands with a hard timeout.
- Keep agent file operations inside `workspace/agent_sandbox/`.

## CI / GitHub Expectations
- GitHub is the canonical remote repository.
- Protect `main` and `develop` with required PRs and required status checks.
- Recommended required checks: `ci`, `gitleaks`, `dependency-review`, `codeql`, `branch-policy`.
- SonarQube is local-only for now, so it should run from local hooks/scripts rather than GitHub-hosted Actions.
