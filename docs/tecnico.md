# Documentación Técnica

## 1. Arquitectura (alto nivel)
- **API Backend (FastAPI)**: superficie HTTP/SSE.
- **Orquestador**: aplica máquina de estados y coordina agentes.
- **Agentes internos**: intercambio A2A mínimo y estructurado.
- **Persistencia (SQLite WAL)**: tareas, eventos, snapshots, locks, idempotencia, métricas.
- **Sandbox de ejecución**: acciones de archivo/shell aisladas.
- **Postura de seguridad**: deny-by-default, mínimo privilegio, validación estricta, auditoría y secretos solo en backend.
- **Modularidad**: los ficheros de agentes deben mantenerse pequeños y cohesionados; objetivo `<= 200` líneas por fichero y refactor obligatorio al acercarse a `300`.

## 1.1 Calidad de código
- **Cobertura mínima**: 90% obligatoria — `pytest` falla si no se alcanza (`--cov-fail-under=90`). Cobertura actual: 98.67%.
- **Análisis estático**: SonarQube local (proyecto `poc-agent4-replit`), ejecutado en pre-push y mediante `scripts/dev/run_sonar.sh`.
- **Reporte de cobertura**: `coverage.xml` (formato Cobertura) generado automáticamente en cada `pytest`, consumido por SonarQube.

## 2. Diseño de API
Rutas principales:
- `POST /api/agent/tasks`
- `GET /api/agent/tasks/{taskId}`
- `GET /api/agent/tasks/{taskId}/events` (SSE)
- `POST /api/agent/tasks/{taskId}/cancel`
- `POST /api/agent/tasks/{taskId}/rollback`
- `POST /api/agent/tasks/{taskId}/resume`
- `GET /api/agent/tasks/{taskId}/result`

## 3. Contrato de respuesta
Éxito:
```json
{ "data": {"taskId": "task_x", "status": "running"}, "meta": {"apiVersion": "v1"} }
```
Error:
```json
{ "error": {"code": "TASK_LOCKED", "message": "...", "retryable": true}, "meta": {"apiVersion": "v1"} }
```

## 4. Persistencia mínima
Tablas:
- `tasks`
- `task_events`
- `snapshots`
- `idempotency_keys`
- `a2a_messages`
- `task_locks`
- `task_artifacts`
- `task_metrics`

## 5. Máquina de estados
Transiciones principales:
- `queued -> running|cancelled`
- `running -> completed|failed|blocked|rolling_back|cancelled`
- `blocked -> running|rolling_back|failed|cancelled`
- `failed -> running|rolling_back|cancelled`
- `rolling_back -> running|blocked|failed|cancelled`

## 6. Rollback atómico
Secuencia obligatoria:
1. Adquirir lock `rolling_back`.
2. Guardar `before_rollback` snapshot.
3. Restaurar archivos + estado en transacción lógica única.
4. Emitir `task_rolled_back`.
5. Liberar lock.

## 7. A2A (interno)
Mensajes cortos y tipados: `handoff | clarify | result | escalate`.
- Enviar referencias (`...Ref`) en lugar de contexto completo.
- Limitar rondas de clarificación.
- Registrar tokens/latencia por mensaje.

## 8. Seguridad y operación
- Seguir **OWASP Top 10** como referencia transversal para diseño, validación, hardening y revisión de vulnerabilidades.
- Backend-only para autenticación con OpenAI.
- **Secret management** obligatorio: no almacenar secretos en plano, cifrar en reposo cualquier credencial/token persistido (**encryption at rest**) y aplicar redacción en logs/errores.
- Aplicar **RBAC** (Role-Based Access Control) y principio de mínimo privilegio para acceso a secretos, operaciones administrativas y futuras capacidades de operador.
- `Idempotency-Key` obligatoria en `resume`.
- Responder `409` en locks/conflictos y `422` en reglas de dominio.
- Auditoría completa vía `task_events`.
- No permitir comandos fuera de allowlist ni ejecución fuera de `workspace/agent_sandbox/`.
- Aplicar timeouts duros y límites de recursos/tokens por defecto.
- Sanitizar logs y respuestas de error para evitar fugas de información sensible.

## 9. Gobernanza de repositorio y calidad
Ramas y flujo:
- Protegidas: `main`, `develop`
- Desde `develop`: `feature/*`, `bugfix/*`, `chore/*`, `docs/*`, `refactor/*`
- Desde `main`: `hotfix/*`
- Desde `develop`: `release/*`
- Opcional: `spike/*`

Reglas:
- Sin commits directos en `main` ni `develop`.
- Sin merges locales a ramas protegidas.
- Integración a ramas protegidas exclusivamente por PR.
- Desarrollo obligatorio mediante **TDD estricto**: `red -> green -> refactor`, escribiendo siempre primero los tests.
- Modularización obligatoria de agentes: extraer helpers, prompts, validadores y coordinación a submódulos para evitar ficheros monolíticos.

Hooks locales esperados:
- `pre-commit`: lint/format, validaciones rápidas de política y `gitleaks`
- `commit-msg`: validación de Conventional Commits
- `pre-push`: tests, política de ramas protegidas y análisis SonarQube local

GitHub Actions recomendadas:
- `ci`
- `gitleaks`
- `dependency-review`
- `codeql`
- `branch-policy`

Notas operativas:
- GitHub será el remoto oficial.
- SonarQube está en local, por lo que su análisis se ejecutará desde hooks/scripts locales y no desde GitHub-hosted Actions mientras no exista runner self-hosted o exposición segura.
