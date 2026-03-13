# ADR 0003: Repository governance, GitFlow, local hooks, and quality controls

- **Status**: Accepted
- **Date**: 2026-03-13

## Context
El proyecto necesita una gobernanza de repositorio y un flujo de integración coherentes con la postura security-first. Además, el repositorio es Python-first, GitHub será el remoto oficial y SonarQube está disponible solo en local mediante Docker.

## Decision
1. GitHub será el repositorio remoto oficial.
2. Se adoptará un GitFlow adaptado con ramas protegidas `main` y `develop`.
3. `main` y `develop` solo podrán actualizarse mediante Pull Request; no se permiten commits directos ni merges locales hacia ramas protegidas.
4. Se permitirán ramas `feature/*`, `bugfix/*`, `chore/*`, `docs/*`, `refactor/*`, `release/*`, `hotfix/*` y `spike/*` opcional.
5. Los mensajes de commit deberán seguir **Conventional Commits**.
6. El desarrollo seguirá **TDD estricto** como regla inamovible: `red -> green -> refactor`, con tests escritos antes del código.
7. Los ficheros de agentes deberán mantenerse modularizados y legibles, con objetivo `<= 200` líneas por fichero y refactor obligatorio antes de superar `300`.
8. Se usarán hooks locales para control preventivo:
   - `pre-commit` para checks rápidos y `gitleaks`
   - `commit-msg` para validar Conventional Commits
   - `pre-push` para tests, validación de política de ramas y análisis SonarQube local
9. Se usarán GitHub Actions para checks remotos ligeros/obligatorios: `ci`, `gitleaks`, `dependency-review`, `codeql` y `branch-policy`.
10. SonarQube se mantendrá fuera de GitHub-hosted Actions mientras siga siendo un servicio local; se ejecutará por hooks/scripts locales.
11. **Se descarta Husky** como mecanismo principal de hooks.

## Consequences
### Positivas
- Refuerza la disciplina de integración y revisión antes de tocar ramas críticas.
- Refuerza la disciplina de desarrollo incremental y validado desde el primer cambio.
- Mantiene el código de agentes más legible y revisable al evitar módulos monolíticos.
- Reduce el riesgo de fuga de secretos con `gitleaks` local y remoto.
- Alinea los controles de calidad con GitHub y con el stack real del proyecto.
- Evita depender de GitHub-hosted Actions para un SonarQube que no es accesible remotamente.
- Mantiene los controles pesados cerca del entorno local y los checks obligatorios en GitHub.

### Negativas
- Incrementa la complejidad operativa del repositorio.
- Obliga a mantener tests al día antes de cualquier implementación.
- Exige refactors más frecuentes para sostener la modularidad.
- Requiere configurar hooks locales y protección de ramas en GitHub.
- Los hooks locales pueden ser evitados si no se acompañan de reglas remotas y CI obligatoria.

## Alternatives considered
- **Permitir commits directos a `develop`**: más ágil, pero reduce trazabilidad y control.
- **Ejecutar SonarQube en GitHub Actions**: no viable mientras SonarQube siga solo en local sin runner self-hosted.
- **Usar Husky como estándar de hooks**: descartado porque el repositorio es Python-first y `pre-commit` encaja mejor en este ecosistema, simplifica la integración de hooks multi-lenguaje y evita introducir dependencia principal de tooling Node para una necesidad que Git y Python ya cubren mejor.
