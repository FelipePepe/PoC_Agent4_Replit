# Documentación Funcional

## 1. Objetivo
Construir un backend de orquestación multi‑agente (PoC) que reciba tareas de desarrollo, las ejecute de forma controlada y entregue resultados auditables al cliente sin exponer detalles de modelos en frontend.

## 2. Alcance
Incluye:
- Alta de tareas de agente
- Seguimiento de estado y progreso
- Streaming de eventos en tiempo real (SSE)
- Cancelación, rollback y reanudación segura
- Resultado final con artefactos y métricas

No incluye (MVP):
- Gestión de usuarios completa
- Billing/costing de producción
- Multi-tenant avanzado

## 3. Actores
- **Frontend/Caller**: crea tareas y consume estado/eventos.
- **Orquestador**: coordina agentes internos.
- **Agentes internos**: planner, editor, verifier, searcher.
- **Operador/Sistema**: puede cancelar o forzar recuperación.

## 4. Casos de uso principales
1. Crear tarea (`POST /api/agent/tasks`) → estado `queued`.
2. Consultar progreso (`GET /api/agent/tasks/{taskId}`).
3. Recibir eventos reactivos (`GET /api/agent/tasks/{taskId}/events`).
4. Cancelar ejecución (`POST /api/agent/tasks/{taskId}/cancel`).
5. Recuperar con rollback (`POST /api/agent/tasks/{taskId}/rollback`).
6. Reanudar (`POST /api/agent/tasks/{taskId}/resume` con `Idempotency-Key`).
7. Obtener resultado (`GET /api/agent/tasks/{taskId}/result`).

## 5. Reglas funcionales clave
- Implementación regida por **security first, security by design y security by default**.
- La implementación y revisión funcional/técnica deben seguir como referencia mínima las recomendaciones de **OWASP Top 10**.
- Frontend **nunca** accede a credenciales/modelos.
- La gestión de secretos es obligatoria: **no plaintext secrets**, acceso solo desde backend, ocultación en logs/errores y cifrado en reposo cuando deban persistirse.
- Rollback debe ser **atómico** (archivos + estado + evento).
- Comunicación reactiva por SSE; evitar polling como mecanismo principal.
- Operaciones críticas (`resume`, `rollback`) deben ser idempotentes.
- Transiciones de estado validadas por máquina de estados.
- Errores y respuestas no deben exponer secretos ni detalles internos sensibles.

## 6. Estados de tarea
`queued`, `running`, `blocked`, `failed`, `rolling_back`, `completed`, `cancelled`.

Estados terminales: `completed`, `cancelled`.

## 7. Reglas funcionales de gobernanza de repositorio
- El repositorio remoto oficial será GitHub.
- `main` y `develop` son ramas protegidas y solo se actualizan mediante Pull Request.
- El flujo de trabajo seguirá GitFlow adaptado: `feature/*`, `bugfix/*`, `chore/*`, `docs/*`, `refactor/*`, `release/*`, `hotfix/*` y `spike/*` opcional.
- Los commits deberán cumplir Conventional Commits.
- Debe existir control preventivo de secretos y calidad antes de integrar cambios.
- La implementación seguirá **TDD estricto** como regla inamovible: `red -> green -> refactor`, siempre test primero y luego código.

## 8. Criterios de éxito MVP
- Flujo extremo a extremo funcional con eventos en tiempo real.
- Errores con contrato estable (`error.code`, `meta.apiVersion`).
- Trazabilidad completa de ejecución y recuperación.
- Gobernanza básica del repositorio operativa: ramas protegidas, PRs y validaciones automáticas/locales definidas.
