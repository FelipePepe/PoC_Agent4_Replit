# ADR 0001: Backend-orchestrated agent execution, atomic rollback, and minimal A2A

- **Status**: Accepted
- **Date**: 2026-03-13

## Context
El PoC requiere aprendizaje real de arquitectura multi‑agente con control operativo: trazabilidad, recuperación ante fallo y aislamiento del frontend respecto a modelos/credenciales.

## Decision
1. El frontend solo consume API propia; la invocación de modelos ocurre exclusivamente en backend.
2. El sistema usará máquina de estados explícita para tareas (`queued` ... `cancelled`).
3. Rollback será atómico y bloqueante (estado `rolling_back` + lock exclusivo).
4. La comunicación A2A será mínima, tipada y con límites de tokens.
5. Reanudación (`resume`) requerirá idempotencia por cabecera `Idempotency-Key`.
6. Canal reactivo oficial: SSE para eventos de tarea.

## Consequences
### Positivas
- Menor exposición de secretos y superficie de ataque.
- Flujo observable y depurable (auditoría por eventos).
- Recuperación más fiable en fallos complejos.
- Coste de tokens más controlable en coordinación multi‑agente.

### Negativas
- Mayor complejidad inicial en backend.
- Necesidad de disciplina estricta en transiciones y locks.
- SSE requiere gestión de reconexión en clientes.

## Alternatives considered
- **Polling puro**: más simple, pero peor latencia y más carga.
- **A2A libre (texto completo)**: flexible, pero coste de tokens impredecible.
- **Sin rollback**: reduce complejidad, pero dificulta aprendizaje y resiliencia.
