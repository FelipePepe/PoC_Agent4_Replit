# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Descripción del Proyecto

PoC de aprendizaje que replica la arquitectura de **Replit Agent 4**: sistema multi-agente con orquestación LangGraph, ejecutado en hardware local (i5, 16GB RAM, sin GPU).

El fichero `poc-agent4-prompt-v2.md` es la especificación canónica del proyecto. Incluirlo como contexto al iniciar cada sesión de trabajo.

## Principios de Seguridad

La implementación de este proyecto debe seguir, desde el inicio, estos principios no negociables:

- **Security first**: la seguridad guía las decisiones de arquitectura, API, persistencia, sandbox y operación.
- **Security by design**: validación estricta, mínimo privilegio, aislamiento, auditoría y control de transiciones se diseñan antes de implementar features.
- **Security by default**: cualquier capacidad no permitida explícitamente debe quedar bloqueada por defecto.
- **OWASP Top 10**: las decisiones de diseño, implementación y revisión deben contrastarse contra este marco como referencia mínima de riesgos web y de aplicación.

Reglas derivadas:

- Backend-only para secretos, credenciales y acceso a modelos/proveedores.
- **Secret management obligatorio**: nunca almacenar secretos en plano; cualquier secreto persistido debe protegerse con **encryption at rest**.
- Aplicar **RBAC** y mínimo privilegio para acceso a secretos, operaciones sensibles y futuras capacidades administrativas.
- Comandos de shell solo mediante allowlist, con timeout duro y alcance de directorios mínimo.
- Todas las entradas deben validarse de forma explícita; rechazar estados, eventos o headers no conformes.
- Los errores y logs no deben filtrar secretos, credenciales, rutas sensibles ni detalles internos innecesarios.
- Mantener trazabilidad auditable de operaciones críticas: creación de tareas, handoffs, rollback, cancelación y resume.

## Gobernanza de Repositorio y Calidad

Repositorio remoto objetivo: **GitHub**.

Política de ramas:

- Ramas protegidas: `main`, `develop`
- Flujo principal: `main <- release/* <- develop <- feature/*`
- Correcciones urgentes: `main <- hotfix/*`
- Correcciones ordinarias: `develop <- bugfix/*`
- Ramas auxiliares permitidas: `chore/*`, `docs/*`, `refactor/*`
- Rama opcional para exploración: `spike/*`

Restricciones:

- No se permiten commits directos en `main` ni en `develop`.
- No se permiten merges locales hacia ramas protegidas.
- `main` y `develop` solo se actualizan vía Pull Request.
- `release/*` y `hotfix/*` deben sincronizarse después con las ramas que corresponda para evitar divergencias.

Controles locales esperados:

- `pre-commit`: validaciones rápidas, formato/lint y `gitleaks`
- `commit-msg`: Conventional Commits
- `pre-push`: tests, checks de ramas protegidas y análisis de SonarQube local cuando aplique

Calidad y seguridad en GitHub:

- Required checks recomendados: `ci`, `gitleaks`, `dependency-review`, `codeql`, `branch-policy`
- Usar `permissions` mínimos en GitHub Actions
- Usar `concurrency` para cancelar ejecuciones obsoletas
- SonarQube no se ejecuta en GitHub Actions mientras siga siendo un servicio local

## Stack

| Componente | Tecnología |
|---|---|
| Lenguaje | Python 3.11+ |
| Orquestación | LangGraph ≥ 0.2.x |
| Observabilidad | LangSmith |
| Modelo principal | Anthropic Claude Sonnet (API) |
| Modelo clasificador | phi3-mini via Ollama (local, CPU) |
| Persistencia | SQLite modo WAL + gitpython |
| Herramientas MCP | MCP SDK oficial Python |

## Setup del Entorno

```bash
pip install langgraph>=0.2 langchain-anthropic langsmith anthropic gitpython mcp

# Modelo local para clasificador (Fase 4+)
ollama pull phi3-mini
```

Variables de entorno requeridas en `.env`:
```
ANTHROPIC_API_KEY=...
LANGSMITH_API_KEY=...
```

## Comandos de Desarrollo

```bash
# Ejecutar el agente principal
python -m core.graph

# Comprobar versión de LangGraph (crítico: 0.1.x y 0.2.x son incompatibles)
python -c "import langgraph; print(langgraph.__version__)"

# Medir latencia de phi3-mini en local
ollama run phi3-mini "test"

# Ejecutar tests
python -m pytest tests/
```

## Arquitectura

### Orden de fases (no reordenar)

```
Fase 0 → Fase 1 → Fase 2 → Fase 6 → Fase 3 → Fase 4 → Fase 5 → Fase 7 → Fase 8
                              ↑
                  Snapshots antes de paralelismo
```

### AgentState (`core/state.py`)

El estado está **definido completo desde Fase 0**. No añadir campos después: rompe los checkpoints guardados.

```python
class AgentState(TypedDict):
    messages:            Annotated[list, add_messages]
    tool_calls:          list
    error_count:         int
    current_model:       str
    task_id:             str
    subtasks:            list
    active_agent:        str
    parallel_results:    dict
    active_instructions: list
    consecutive_errors:  int
    model_switches:      int
    snapshot_id:         str | None
```

### Agentes (`agents/`)

- `supervisor.py` — orquesta el flujo global, decide qué agente actúa
- `planner.py` — descompone tareas en subtareas ordenadas
- `editor.py` — escribe y modifica código
- `verifier.py` — valida resultados ejecutando tests
- `searcher.py` — busca documentación
- Mantener cada fichero de agente pequeño y legible: objetivo `<= 200` líneas; si crece, extraer utilidades, prompts, políticas o lógica de coordinación a submódulos. `300` líneas es umbral máximo antes de refactor obligatorio.

### Componentes core

- `core/graph.py` — definición del grafo LangGraph
- `core/models.py` — lógica de switch entre modelos (Sonnet → Haiku → Ollama)
- `core/db.py` — init SQLite con `PRAGMA journal_mode=WAL;`
- `guidance/classifier.py` — `TrajectoryClassifier` con phi3-mini; activa solo si `consecutive_errors >= 2` o contexto supera umbral
- `snapshots/engine.py` — `SnapshotEngine`: `take_snapshot`, `restore_snapshot`, `list_snapshots`

### Sandbox del agente

El agente trabaja **exclusivamente** en `workspace/agent_sandbox/`. Nunca en el directorio raíz del proyecto. `execute_shell` requiere lista blanca de comandos y timeout duro de 10 segundos.

### Switch de modelos (Fase 5+)

| consecutive_errors | Modelo |
|---|---|
| < 3 | Claude Sonnet |
| ≥ 3 | Claude Haiku |
| ≥ 6 | Ollama local |

Retorno automático a Sonnet tras resolución exitosa.

### Micro-instrucciones (Fase 4+)

Las instrucciones inyectadas por el clasificador se añaden al **final del contexto** (nunca al system prompt) y **no persisten** en el historial tras la resolución.

## Restricciones de Hardware

- phi3-mini en CPU: 3–8 segundos por inferencia → llamar solo bajo condición, nunca en cada paso del loop
- SQLite WAL activado desde Fase 0 para soportar escrituras concurrentes en Fase 3

## Reglas de Desarrollo

- **TDD estricto es una regla inamovible**: seguir siempre `red -> green -> refactor`, escribiendo primero el test y después el código.
- Trabajar **una fase a la vez**. Los criterios de salida son innegociables.
- Si un ítem bloquea >30 minutos: documentar con `# BLOCKED:` y continuar.
- Ante dudas arquitectónicas: **la opción más simple que funcione correctamente**.
- Si hay duda entre comodidad y seguridad, elegir la opción más segura compatible con el objetivo de aprendizaje.
- Antes de proponer automatizaciones de repositorio, respetar siempre la política de ramas protegidas y PR obligatoria.
- Ningún fichero de agente debe concentrar demasiada responsabilidad: modularizar antes de que deje de ser legible.
- Decisiones ya cerradas (no reabrir):
  - SQLite sobre PostgreSQL
  - Sin Docker en fases iniciales
  - phi3-mini sobre GPT-4 para el clasificador
