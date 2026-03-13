# PoC: Replit Agent 4 Clone — Prompt de Desarrollo v2

## Contexto del Proyecto

Eres un senior software architect con 20+ años de experiencia. Vamos a construir un **PoC de aprendizaje** que replica la arquitectura de Replit Agent 4, ejecutándose en un portátil i5 con 16GB RAM, sin GPU dedicada. El objetivo no es producción ni mostrar a nadie — es entender cada pieza construyéndola.

**Stack decidido:**

| Componente | Tecnología |
|---|---|
| Lenguaje | Python 3.11+ |
| Orquestación de agentes | LangGraph ≥ 0.2.x (Python) |
| Observabilidad | LangSmith |
| Modelo principal | Anthropic Claude Sonnet (API) |
| Modelo clasificador | phi3-mini via Ollama (local, CPU) |
| Persistencia de estado | SQLite en modo WAL + gitpython |
| Herramientas MCP | MCP SDK oficial Python |
| Entorno | Local, sin Docker por ahora |

**Restricciones de hardware a tener en cuenta:**
- phi3-mini en CPU tardará 3–8 segundos por inferencia → llamarlo solo bajo condición, nunca en cada paso del loop
- SQLite con escrituras concurrentes en Fase 3 → activar WAL mode desde Fase 0
- Sin aislamiento de red → sandboxear `execute_shell` con lista de comandos permitidos y timeout duro desde Fase 1

**Principios de desarrollo:**
- Cada fase debe ser funcional antes de pasar a la siguiente
- Código simple y legible primero, optimizar después
- Cada componente debe ser comprensible de forma aislada
- Sin over-engineering — es un PoC de aprendizaje

---

## AgentState Base — Definir desde Fase 0

> ⚠️ **Crítico:** Definir el estado completo desde el principio. Añadir campos en fases posteriores rompe los checkpoints guardados y obliga a refactorizaciones costosas.

```python
# core/state.py
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    # --- Fase 1 ---
    messages:            Annotated[list, add_messages]  # historial de mensajes
    tool_calls:          list                           # herramientas invocadas
    error_count:         int                            # errores totales acumulados
    current_model:       str                            # modelo activo ahora mismo

    # --- Fase 2 ---
    task_id:             str                            # identificador de tarea
    subtasks:            list                           # subtareas descompuestas por PlannerAgent
    active_agent:        str                            # agente actualmente en control

    # --- Fase 3 ---
    parallel_results:    dict                           # resultados de sub-agentes paralelos

    # --- Fase 4 ---
    active_instructions: list                          # micro-instrucciones efímeras inyectadas
    consecutive_errors:  int                           # errores seguidos sin éxito

    # --- Fase 5 ---
    model_switches:      int                           # cuántas veces se ha cambiado de modelo

    # --- Fase 6 ---
    snapshot_id:         str | None                    # id del último snapshot activo
```

---

## Orden de Fases (Revisado)

> El orden original de las fases 3 y 6 está invertido. Los snapshots deben existir **antes** de introducir ejecución paralela — sin ellos, un estado corrupto por race condition es prácticamente imposible de depurar.

```
Fase 0 → Fase 1 → Fase 2 → Fase 6 → Fase 3 → Fase 4 → Fase 5 → Fase 7 → Fase 8
                             ↑
                     Snapshots primero, paralelo después
```

---

## Checklist de Fases

### FASE 0 — Entorno y Fundamentos
> Objetivo: tener el entorno listo y entender los primitivos de LangGraph

- [ ] Instalar dependencias base: `langgraph>=0.2`, `langchain-anthropic`, `langsmith`, `anthropic`
- [ ] Instalar Ollama y descargar `phi3-mini` (`ollama pull phi3-mini`)
- [ ] Configurar variables de entorno: `ANTHROPIC_API_KEY`, `LANGSMITH_API_KEY`
- [ ] Crear proyecto Python con estructura de carpetas base (ver sección al final)
- [ ] Inicializar SQLite con `PRAGMA journal_mode=WAL;` desde el primer momento
- [ ] Implementar un grafo LangGraph mínimo: un solo nodo, un estado, sin edges condicionales
- [ ] Verificar trazas en LangSmith (al menos una traza visible antes de continuar)
- [ ] Documentar la estructura del `AgentState` base completo (usar la definición de arriba)

**Criterio de salida:** Un grafo que recibe un mensaje, llama a Claude y devuelve la respuesta, con traza visible en LangSmith.

**Riesgo conocido:** LangGraph 0.1.x y 0.2.x tienen APIs incompatibles. Muchos ejemplos en internet son de la versión antigua. Verificar siempre la versión instalada antes de copiar código externo.

---

### FASE 1 — Agente Simple con Herramientas (ReAct)
> Objetivo: entender el bucle ReAct y la ejecución de herramientas

- [ ] Usar el `AgentState` completo definido en Fase 0
- [ ] Implementar nodo `supervisor`: planifica y decide qué herramienta usar
- [ ] Definir sandbox antes de implementar herramientas:
  - [ ] Directorio de trabajo aislado: `workspace/agent_sandbox/` (nunca el proyecto raíz)
  - [ ] Lista blanca de comandos permitidos para `execute_shell`
  - [ ] Timeout duro de 10 segundos por comando
  - [ ] Nunca ejecutar como root
- [ ] Implementar herramientas básicas via función Python:
  - [ ] `read_file(path)` — solo dentro del sandbox
  - [ ] `write_file(path, content)` — solo dentro del sandbox
  - [ ] `execute_shell(command)` — sandboxeado según definición anterior
  - [ ] `search_web(query)` — búsqueda simple (puede ser mock en esta fase)
- [ ] Implementar bucle ReAct: supervisor → herramienta → resultado → supervisor
- [ ] Añadir nodo `verifier`: comprueba si el resultado es correcto
- [ ] Implementar condición de salida: tarea completada O máximo de iteraciones (límite: 10)
- [ ] Logging de cada paso del bucle con nivel INFO

**Criterio de salida:** El agente recibe "crea un fichero hello.py que imprima Hola Mundo" y lo hace, con bucle ReAct visible en logs y el fichero creado dentro del sandbox.

---

### FASE 2 — Arquitectura Multi-Agente
> Objetivo: replicar el patrón supervisor + sub-agentes especializados de Replit

- [ ] Refactorizar en agentes especializados:
  - [ ] `PlannerAgent`: descompone la tarea en subtareas concretas y ordenadas
  - [ ] `EditorAgent`: escribe y modifica código
  - [ ] `VerifierAgent`: valida el resultado (ejecuta tests, inspecciona output)
  - [ ] `SearchAgent`: busca documentación e información
- [ ] Implementar `SupervisorAgent`: orquesta a los demás, gestiona el estado global
- [ ] Definir protocolo de comunicación entre agentes (mensajes tipados en el estado)
- [ ] Implementar handoff entre agentes: cómo el supervisor delega y recoge resultados
- [ ] Añadir scope mínimo por agente (cada uno solo tiene las herramientas que necesita)
- [ ] Test de integración: tarea compleja que requiera al menos 3 agentes

**Criterio de salida:** El agente descompone "crea una API REST en Flask con un endpoint /ping" y cada sub-agente hace su parte, con el resultado verificado por `VerifierAgent`.

---

### FASE 6 — Snapshots y Rollback *(antes de paralelo)*
> Objetivo: tener red de seguridad antes de introducir complejidad de paralelismo

- [ ] Instalar `gitpython`
- [ ] Definir estructura de un `Snapshot`:
  ```python
  { "snapshot_id": str, "timestamp": str, "git_commit": str,
    "state_json": str, "task_id": str, "trigger": str }
  ```
- [ ] Implementar `SnapshotEngine`:
  - [ ] `take_snapshot(state, trigger)` → commit git + guardar estado en SQLite
  - [ ] `restore_snapshot(snapshot_id)` → revertir ficheros + restaurar estado
  - [ ] `list_snapshots(task_id)` → historial de checkpoints de una tarea
- [ ] Separar estado de "producción" (tu código real) de "sandbox del agente" en gitignore
- [ ] Definir política de cuándo hacer snapshot: antes de `write_file` y `execute_shell`
- [ ] Test: el agente hace un cambio erróneo, rollback al snapshot anterior

**Criterio de salida:** El agente modifica un fichero incorrectamente, se detecta el error, y `restore_snapshot()` devuelve el fichero a su estado anterior, verificado por diff.

---

### FASE 3 — Ejecución Paralela
> Objetivo: replicar el "Move Faster" de Agent 4 — sub-agentes ejecutando en paralelo

- [ ] Revisar cómo LangGraph implementa paralelismo con `Send()` o branches paralelos
- [ ] Identificar qué subtareas son independientes entre sí (sin dependencias de datos)
- [ ] Implementar ejecución paralela con `asyncio` en LangGraph
- [ ] Verificar que SQLite WAL mode (configurado en Fase 0) aguanta las escrituras concurrentes
- [ ] Implementar nodo `merge`: combina resultados de agentes paralelos
- [ ] Implementar `ConflictResolver`: detecta y resuelve conflictos entre resultados paralelos
- [ ] Añadir estado de progreso visible por tarea paralela en el log
- [ ] Medir speedup real vs. secuencial (loggear tiempos de inicio y fin por agente)
- [ ] Test: tarea con 3+ subtareas independientes ejecutadas en paralelo

**Criterio de salida:** Dos sub-agentes ejecutan simultáneamente y sus resultados se fusionan correctamente. Tiempo total < suma de tiempos secuenciales. Si hay fallo, el snapshot de Fase 6 permite rollback.

---

### FASE 4 — Guía en Tiempo de Decisión (Decision-Time Guidance)
> Objetivo: la pieza más interesante — clasificador que inyecta micro-instrucciones efímeras

- [ ] Verificar rendimiento de phi3-mini en local antes de diseñar la integración:
  - Medir latencia de inferencia en tu hardware
  - Confirmar que es viable llamarlo bajo condición (no en cada paso)
- [ ] Definir biblioteca de micro-instrucciones (empezar con 10–15):
  - Para bucles de error repetidos (consecutive_errors >= 3)
  - Para cuando el agente se atasca en un mismo fichero (mismo tool_call repetido)
  - Para cuando hay demasiadas herramientas fallidas
  - Para cuando el contexto crece por encima de umbral (e.g. >8000 tokens)
  - Para cuando el plan original ya no encaja con el estado actual
- [ ] Implementar `TrajectoryClassifier`:
  - Input: últimos N mensajes + tool_results + consecutive_errors + tokens usados
  - Output: lista de etiquetas de situación detectada
  - Activación: solo cuando `consecutive_errors >= 2` O contexto supera umbral
- [ ] Implementar inyección efímera: la micro-instrucción se añade al final del contexto, **no al system prompt**
- [ ] Verificar que las instrucciones inyectadas **no persisten** en el historial tras resolución
- [ ] Loggear qué instrucciones se activan, cuándo y con qué resultado
- [ ] Comparar ejecuciones con y sin guía en tareas que suelen fallar

**Criterio de salida:** El clasificador detecta un bucle de error (`consecutive_errors >= 3`) y la micro-instrucción inyectada cambia el comportamiento del agente en la siguiente iteración, medible en los logs.

---

### FASE 5 — Consulta a Modelo Diferente (Anti-Doom-Loop)
> Objetivo: romper bucles de fallo cambiando de perspectiva de modelo

- [ ] Confirmar que `error_count`, `consecutive_errors` y `model_switches` están en el estado (ya definidos en Fase 0)
- [ ] Definir umbrales:
  - Nivel 0 → Claude Sonnet (modelo principal, `consecutive_errors < 3`)
  - Nivel 1 → Claude Haiku (`consecutive_errors >= 3`, primer switch)
  - Nivel 2 → modelo local Ollama (`consecutive_errors >= 6`, segundo switch)
- [ ] El agente "consultor" recibe: historial completo + descripción del bloqueo + intentos previos
- [ ] Implementar retorno automático a Claude Sonnet tras resolución exitosa
- [ ] Loggear todos los switches: modelo origen, modelo destino, motivo, resultado
- [ ] Test: provocar un bucle de fallo deliberado (herramienta que siempre falla) y observar el switch automático

**Criterio de salida:** Ante 3 fallos consecutivos, el sistema cambia de modelo automáticamente, lo documenta en logs con motivo, y retorna al modelo principal cuando el problema se resuelve.

---

### FASE 7 — Integración MCP
> Objetivo: conectar herramientas externas via Model Context Protocol

- [ ] Instalar `mcp` SDK Python oficial
- [ ] Implementar servidor MCP local con herramientas básicas:
  - [ ] `filesystem` — operaciones de fichero via MCP (reemplaza tools/filesystem.py)
  - [ ] `shell` — ejecución de comandos via MCP (con las mismas restricciones de sandbox de Fase 1)
- [ ] Conectar el agente al servidor MCP (reemplazar llamadas directas a funciones)
- [ ] Añadir un servidor MCP externo de ejemplo (e.g. búsqueda web via MCP)
- [ ] Verificar que el agente descubre herramientas MCP dinámicamente sin hardcoding
- [ ] Documentar la diferencia de experiencia vs. function-calling directo

**Criterio de salida:** El agente usa al menos una herramienta registrada en el servidor MCP local sin que esté hardcodeada en su configuración. El agente la descubre en runtime.

---

### FASE 8 — Integración y Demo Final
> Objetivo: que todos los pilares trabajen juntos en una tarea real

- [ ] Definir tarea de demo representativa: *"crea una app Flask CRUD con tests y documentación"*
- [ ] Ejecutar con todos los sistemas activos:
  - [ ] Multi-agente paralelo (Fase 3)
  - [ ] Guía en tiempo de decisión (Fase 4)
  - [ ] Anti-doom-loop (Fase 5)
  - [ ] Snapshots automáticos (Fase 6)
  - [ ] Herramientas via MCP (Fase 7)
- [ ] Revisar trazas completas en LangSmith
- [ ] Documentar qué funcionó bien y qué no en un post-mortem honesto
- [ ] Anotar diferencias arquitectónicas con Replit Agent 4 real (qué simplificamos y por qué)
- [ ] Escribir README técnico del PoC

**Criterio de salida:** La tarea de demo se completa de extremo a extremo con todos los sistemas activos y trazas completas en LangSmith.

---

## Estructura de Carpetas

```
poc-agent4/
├── agents/
│   ├── supervisor.py
│   ├── planner.py
│   ├── editor.py
│   ├── verifier.py
│   └── searcher.py
├── core/
│   ├── state.py          # AgentState completo (definido desde Fase 0)
│   ├── graph.py          # Definición del grafo LangGraph
│   ├── models.py         # Configuración y lógica de switch de modelos
│   └── db.py             # Inicialización de SQLite con WAL mode
├── guidance/
│   ├── classifier.py     # TrajectoryClassifier (phi3-mini via Ollama)
│   └── instructions.py   # Banco de micro-instrucciones
├── snapshots/
│   ├── engine.py         # SnapshotEngine (take, restore, list)
│   └── storage.py        # SQLite para metadatos de snapshots
├── mcp/
│   └── server.py         # Servidor MCP local
├── tools/
│   ├── filesystem.py     # Reemplazado por MCP en Fase 7 (mantener como fallback)
│   ├── shell.py          # Reemplazado por MCP en Fase 7 (mantener como fallback)
│   └── search.py
├── workspace/
│   └── agent_sandbox/    # Directorio de trabajo aislado del agente
├── tests/
│   └── ...
├── .env
├── requirements.txt
└── README.md
```

---

## Notas de Uso del Prompt

- Trabajar **una fase a la vez**. No avanzar hasta marcar todos los ítems de la fase.
- Incluir este fichero como contexto inicial en cada nueva conversación sobre el PoC.
- Si un ítem bloquea más de 30 minutos, documentar el bloqueo en un comentario `# BLOCKED:` y continuar — volver después.
- Los criterios de salida son innegociables: si no se cumplen, la fase no está terminada.
- Ante cualquier duda arquitectónica, la regla es: **la opción más simple que funcione correctamente**.
- Decisiones ya tomadas y cerradas (no reabrir sin motivo mayor):
  - SQLite sobre PostgreSQL: suficiente para PoC local, evita complejidad operacional
  - Sin Docker en fases iniciales: sandbox manual es suficiente y más transparente para aprender
  - phi3-mini sobre GPT-4 para clasificador: el objetivo es local y bajo coste, no máxima precisión
