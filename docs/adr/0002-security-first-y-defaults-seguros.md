# ADR 0002: Security-first, secure-by-design, and secure-by-default implementation

- **Status**: Accepted
- **Date**: 2026-03-13

## Context
El PoC no debe tratar la seguridad como hardening posterior. La implementación debe nacer con una postura de seguridad explícita porque el sistema orquesta agentes, ejecuta acciones potencialmente sensibles y gestionará credenciales/modelos solo desde backend.

## Decision
1. El proyecto adoptará **security first** como criterio rector de arquitectura e implementación.
2. Se aplicará **security by design**: validación estricta, aislamiento, mínimo privilegio, auditoría y control de transiciones se diseñan desde el inicio.
3. Se aplicará **security by default**: cualquier capacidad no permitida explícitamente quedará bloqueada por defecto.
4. Se tomará **OWASP Top 10** como baseline obligatorio de revisión para riesgos de aplicación, validación de entradas, control de acceso, exposición criptográfica, logging y dependencias.
5. El sistema seguirá una política **deny-by-default** para comandos, rutas, endpoints expuestos y transiciones de estado.
6. Los secretos, credenciales y acceso a proveedores/modelos permanecerán exclusivamente en backend.
7. Se aplicará **secret management** obligatorio: no plaintext secrets, **encryption at rest** para secretos persistidos y redacción en logs/errores/eventos.
8. Se aplicará **RBAC** (Role-Based Access Control) y mínimo privilegio para acceso a secretos y operaciones sensibles.
9. Los errores, logs y eventos deberán sanitizarse para no exponer secretos ni detalles internos innecesarios.
10. Se impondrán límites y defaults seguros: timeouts duros, presupuestos acotados de recursos/tokens y validación explícita de entradas y cabeceras.

## Consequences
### Positivas
- Reduce la superficie de ataque desde el primer diseño.
- Aporta un marco reconocible para revisar riesgos frecuentes y evitar omisiones de seguridad comunes.
- Evita que el MVP dependa de hardening tardío y difícil de retrofitar.
- Obliga a diseñar sandboxing, validación y auditoría como partes centrales del sistema.
- Obliga a tratar secretos y permisos como decisiones arquitectónicas explícitas.
- Facilita revisiones de seguridad y decisiones consistentes durante la implementación.

### Negativas
- Añade fricción inicial al desarrollo del PoC.
- Requiere más trabajo de validación y manejo explícito de errores desde fases tempranas.
- Puede retrasar decisiones “rápidas” si no cumplen la postura segura por defecto.

## Alternatives considered
- **Hardening al final**: más rápido al inicio, pero arriesga reescrituras y omisiones críticas.
- **Seguridad selectiva solo en componentes sensibles**: reduce esfuerzo inmediato, pero deja inconsistencias y huecos operativos.
