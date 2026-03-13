# Git Workflow y Controles de Calidad

## 1. Objetivo
Definir la gobernanza del repositorio, el flujo de ramas y los controles de calidad/seguridad que deben aplicarse antes de integrar cambios.

## 2. Repositorio remoto
- El remoto canónico del proyecto es **GitHub**.
- Las ramas `main` y `develop` deben configurarse como **protegidas**.

## 3. Modelo de ramas
Ramas permanentes:
- `main`
- `develop`

Ramas temporales:
- `feature/*` desde `develop`
- `bugfix/*` desde `develop`
- `chore/*` desde `develop`
- `docs/*` desde `develop`
- `refactor/*` desde `develop`
- `release/*` desde `develop`
- `hotfix/*` desde `main`
- `spike/*` opcional, normalmente desde `develop`

## 4. Reglas obligatorias
- No se permiten commits directos en `main`.
- No se permiten commits directos en `develop`.
- No se permiten merges locales hacia ramas protegidas.
- `main` solo se actualiza mediante PR desde `release/*` o `hotfix/*`.
- `develop` solo se actualiza mediante PR desde ramas de trabajo permitidas.
- Los mensajes de commit deben seguir **Conventional Commits**.
- El desarrollo sigue **TDD estricto** como regla inamovible: `red -> green -> refactor`, siempre test primero y código después.
- Los ficheros de agentes deben mantenerse pequeños y legibles; objetivo `<= 200` líneas y refactor obligatorio antes de superar `300`.

## 5. Hooks locales previstos
### `pre-commit`
Checks rápidos:
- formateo/lint
- validaciones de política del repositorio
- escaneo de secretos con `gitleaks`

### `commit-msg`
- validación de Conventional Commits

### `pre-push`
Checks más pesados:
- tests
- validación de ramas protegidas
- análisis SonarQube local cuando aplique

Instalación prevista cuando el entorno esté listo:
```bash
pip install ".[dev]"
python scripts/git_hooks/install_hooks.py
```

Nota:
- `gitleaks` no se instala desde `pip` en este proyecto; debe estar disponible como binario del sistema para que los hooks lo ejecuten.

Activación rápida del entorno virtual:
```bash
source scripts/dev/enter_venv.sh
```

## 6. SonarQube
- SonarQube corre en local (Docker).
- Mientras siga siendo local, **no** se integrará en GitHub-hosted Actions.
- Su uso previsto es mediante hooks locales o scripts manuales previos a push/PR.
- Si en el futuro existe un runner self-hosted con acceso al servicio, podrá reevaluarse la integración en Actions.

## 7. GitHub Actions recomendadas
Checks remotos recomendados para PRs:
- `ci`
- `gitleaks`
- `dependency-review`
- `codeql`
- `branch-policy`

Buenas prácticas adicionales:
- `permissions` mínimos para `GITHUB_TOKEN`
- `concurrency` para cancelar ejecuciones obsoletas
- checks requeridos en `main` y `develop`

## 8. Relación con security-first
Esta política de repositorio forma parte de la postura **security first / by design / by default**:
- reduce riesgo de integración insegura
- evita filtrado accidental de secretos
- fuerza revisión antes de tocar ramas críticas
- establece trazabilidad y calidad mínima antes de merge
