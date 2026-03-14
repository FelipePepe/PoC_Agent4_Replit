# Git Workflow y Controles de Calidad

## 1. Objetivo
Definir la gobernanza del repositorio, el flujo de ramas y los controles de calidad/seguridad que deben aplicarse antes de integrar cambios.

## 2. Repositorio remoto
- Remoto canónico: **GitHub** → `https://github.com/FelipePepe/PoC_Agent4_Replit` (público)
- Ramas `main` y `develop` configuradas como **protegidas** (PR obligatoria, no force push, no delete).
- Rama por defecto: `main`.
- Rama activa de trabajo: `feature/core-base-implementation`.

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

## 6. Scripts de hooks — referencia detallada

Todos los scripts viven en `scripts/git_hooks/` y están escritos en Python 3.11+.
Se invocan desde los hooks de git gestionados por `pre-commit` o escritos
directamente en `.git/hooks/` por `install_hooks.py`.

---

### `install_hooks.py`
**Hook de git:** ninguno (script de instalación, se ejecuta manualmente).

**Propósito:** instalar todos los hooks del proyecto en el repositorio local con
un solo comando.

**Qué hace:**
1. Ejecuta `pre-commit install` → instala el hook `pre-commit`.
2. Ejecuta `pre-commit install --hook-type pre-push` → instala el hook `pre-push`.
3. Escribe `.git/hooks/commit-msg` apuntando a `validate_commit_msg.py`.
4. Escribe `.git/hooks/pre-merge-commit` apuntando a `check_merge_commit.py`.

**Uso:**
```bash
source scripts/dev/enter_venv.sh   # activar venv
python scripts/git_hooks/install_hooks.py
```

---

### `check_protected_branch.py`
**Hook de git:** `pre-commit` (vía `.pre-commit-config.yaml`).

**Propósito:** impedir commits directos en ramas protegidas (`main`, `develop`).

**Cómo funciona:**
1. Comprueba si el repositorio ya tiene commits (`git rev-parse --verify HEAD`).
   - Si no los tiene (primer commit del repo), sale con éxito — el seed commit
     en `main` debe poder hacerse.
2. Obtiene la rama actual con `git symbolic-ref --short HEAD`.
   - Si HEAD está desconectado (`detached HEAD`), sale con éxito.
3. Si la rama está en `PROTECTED_BRANCHES`, imprime un error y sale con código 1,
   abortando el commit.

**Patrón clave — detección de HEAD unborn:**
```python
def _has_commits() -> bool:
    result = subprocess.run(["git", "rev-parse", "--verify", "HEAD"], ...)
    return result.returncode == 0
```
Usar `rev-parse --verify HEAD` (no `--abbrev-ref`) es la forma correcta de
detectar un repositorio sin commits; `--abbrev-ref` falla con exit 128 en ese
estado.

---

### `check_branch_naming.py`
**Hook de git:** `pre-commit` (vía `.pre-commit-config.yaml`).

**Propósito:** asegurar que el nombre de la rama activa sigue la convención
GitFlow del proyecto antes de aceptar un commit.

**Patrones permitidos** (expresiones regulares con `re.fullmatch`):

| Patrón | Uso |
|---|---|
| `main` | rama de producción |
| `develop` | rama de integración |
| `feature/[a-z0-9._-]+` | nueva funcionalidad |
| `bugfix/[a-z0-9._-]+` | corrección en desarrollo |
| `chore/[a-z0-9._-]+` | tareas de mantenimiento |
| `docs/[a-z0-9._-]+` | solo documentación |
| `refactor/[a-z0-9._-]+` | refactorización sin cambio funcional |
| `release/[a-z0-9._-]+` | preparación de release |
| `hotfix/[a-z0-9._-]+` | corrección urgente desde `main` |
| `spike/[a-z0-9._-]+` | exploración/experimento |

Aplica el mismo tratamiento de HEAD unborn y detached HEAD que
`check_protected_branch.py`.

---

### `check_merge_commit.py`
**Hook de git:** `pre-merge-commit` (escrito por `install_hooks.py`).

**Propósito:** bloquear merge commits locales en ramas protegidas.

**Cómo funciona:**
1. Obtiene la rama actual.
2. Cuenta los padres del HEAD actual con `git rev-list --parents -n 1 HEAD`.
   Un merge commit tiene más de un padre.
3. Si la rama es protegida **y** el commit tiene más de un padre, aborta.

**Por qué importa:** en GitFlow, las integraciones a `main` y `develop` solo
deben ocurrir mediante Pull Requests en GitHub. Un merge local saltaría las
revisiones y checks de CI requeridos.

---

### `validate_commit_msg.py`
**Hook de git:** `commit-msg` (escrito por `install_hooks.py`).

**Propósito:** validar que el mensaje de commit sigue el formato
[Conventional Commits](https://www.conventionalcommits.org/).

**Formato esperado:**
```
<tipo>[(<scope>)][!]: <descripción>
```

**Tipos aceptados:** `feat`, `fix`, `docs`, `style`, `refactor`, `test`,
`chore`, `build`, `ci`, `perf`, `revert`.

**Expresión regular usada:**
```python
r"^(feat|fix|docs|style|refactor|test|chore|build|ci|perf|revert)"
r"(\([a-z0-9._/-]+\))?!?: .+"
```

El `!` opcional indica un breaking change. El scope entre paréntesis es
opcional pero recomendado (p.ej. `feat(core): add task state machine`).

**Ejemplos válidos:**
```
feat(core): add task state machine
fix: handle unborn HEAD in branch check
docs(adr): add security-first ADR
chore!: drop Python 3.10 support
```

---

### `run_gitleaks.py`
**Hook de git:** `pre-commit` (vía `.pre-commit-config.yaml`).

**Propósito:** escanear el repositorio en busca de secretos accidentales
(claves API, tokens, contraseñas) antes de cada commit.

**Cómo funciona:**
1. Comprueba si el binario `gitleaks` está disponible en el PATH con
   `shutil.which("gitleaks")`.
2. Si no está instalado, imprime un aviso y sale con éxito (degradación
   controlada — no bloquea el flujo durante el setup inicial).
3. Si está instalado, ejecuta:
   ```
   gitleaks detect --no-banner --redact --source .
   ```
   - `--redact`: oculta el valor del secreto detectado en la salida.
   - `--no-banner`: suprime el banner de gitleaks para no contaminar los logs.

**Instalación de gitleaks:**
```bash
# macOS
brew install gitleaks

# Linux — descargar release desde GitHub
https://github.com/gitleaks/gitleaks/releases
```

---

## 7. SonarQube
- SonarQube corre en local (Docker, contenedor `sonarqube-custom`, http://localhost:9000).
- Proyecto: `poc-agent4-replit` | Perfil de calidad: *Sonar way* (306 reglas Python activas).
- Mientras siga siendo local, **no** se integrará en GitHub-hosted Actions.
- Su uso previsto es mediante hooks locales o scripts manuales previos a push/PR.
- Si en el futuro existe un runner self-hosted con acceso al servicio, podrá reevaluarse la integración en Actions.

### Configuración técnica
- `sonar-project.properties` en la raíz del proyecto (no incluir el token aquí).
- `sonar.python.coverage.reportPaths=coverage.xml` — SonarQube lee el XML de Cobertura, no el output de terminal.
- El token se gestiona via variable de entorno `SONAR_TOKEN` en `.env` (gitignoreado).

### Cobertura
- `coverage.xml` se genera automáticamente con cada `pytest` (configurado en `pyproject.toml`).
- Requisito mínimo: **90%** de cobertura — la suite falla si no se alcanza (`--cov-fail-under=90`).
- Cobertura actual: **98.67%**.
- Para que SonarQube resuelva los paths correctamente: `source = ["."]` + `relative_files = true` en `[tool.coverage.run]`.

### Scripts de análisis
- `scripts/dev/run_sonar.sh` — ejecuta análisis manual vía Docker (genera `coverage.xml` primero).
- `scripts/git_hooks/run_sonar.py` — wrapper para el hook `pre-push` (falla de forma controlada si Docker o token no están disponibles).

## 8. GitHub Actions recomendadas
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

## 9. Relación con security-first
Esta política de repositorio forma parte de la postura **security first / by design / by default**:
- reduce riesgo de integración insegura
- evita filtrado accidental de secretos
- fuerza revisión antes de tocar ramas críticas
- establece trazabilidad y calidad mínima antes de merge
