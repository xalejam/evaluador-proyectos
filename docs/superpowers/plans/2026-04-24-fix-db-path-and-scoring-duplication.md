# Plan 2: Centralizar DB_PATH y Eliminar Scoring Duplicado

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminar el string `"project_viability.db"` hardcodeado en 8+ archivos y la lógica de scoring duplicada entre `score_engine.py` y `planning.py`, reemplazando ambas con una única fuente de verdad.

**Architecture:** Se crea `config/constants.py` con `DB_PATH` como constante absoluta resuelta en tiempo de import. Todos los archivos que usaban el string literal lo reemplazan con `from config.constants import DB_PATH`. La lógica de `_impact_points`/`_risk_points`/`_complexity_points` duplicada en `planning.py` se elimina — ya existe en `domain/scoring/score_engine.py`.

**Tech Stack:** Python stdlib (`pathlib`), pytest.

---

## Estructura de archivos

| Archivo | Acción | Cambio |
|---|---|---|
| `config/constants.py` | Crear | `DB_PATH`, `MATRIX_DB_PATH`, `DEFAULT_AUTHOR` centralizados |
| `infra/db_migrations.py` | Modificar | Importar `DB_PATH` desde `config.constants` |
| `infra/db/connection.py` | Modificar | Importar `DB_PATH` desde `config.constants` |
| `infra/db/repositories/project_repo.py` | Modificar | Importar `DB_PATH` desde `config.constants` |
| `infra/db/repositories/evaluation_repo.py` | Modificar | Importar `DB_PATH` desde `config.constants` |
| `infra/db/repositories/notes_repo.py` | Modificar | Importar `DB_PATH` desde `config.constants` |
| `domain/services/viability_service.py` | Modificar | Importar `DB_PATH` desde `config.constants` |
| `domain/services/seguimiento_operativo_service.py` | Modificar | Importar `DB_PATH` desde `config.constants` |
| `ui/tabs/shared.py` | Modificar | Importar `DB_PATH` desde `config.constants` |
| `ui/use_case_matrix.py` | Modificar | Importar `DB_PATH` desde `config.constants` |
| `ui/tabs/planning.py` | Modificar | Eliminar funciones `_impact_points`, `_risk_points`, `_complexity_points` duplicadas |
| `ui/state.py` | Modificar | Reemplazar `"Xiomy"` con `DEFAULT_AUTHOR` |
| `tests/unit/test_constants.py` | Crear | Verifica que `DB_PATH` es absoluto y `DEFAULT_AUTHOR` no es hardcoded |

---

## Task 1: Crear `config/constants.py`

**Files:**
- Create: `config/constants.py`
- Test: `tests/unit/test_constants.py`

- [ ] **Step 1: Escribir el test**

```python
# tests/unit/test_constants.py
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from config.constants import DB_PATH, MATRIX_DB_PATH, DEFAULT_AUTHOR


def test_db_path_is_absolute():
    assert Path(DB_PATH).is_absolute(), f"DB_PATH debe ser absoluto, got: {DB_PATH}"


def test_matrix_db_path_is_absolute():
    assert Path(MATRIX_DB_PATH).is_absolute(), f"MATRIX_DB_PATH debe ser absoluto, got: {MATRIX_DB_PATH}"


def test_default_author_is_not_xiomy():
    assert DEFAULT_AUTHOR != "Xiomy", "DEFAULT_AUTHOR no debe ser un nombre personal hardcodeado"


def test_db_path_ends_with_expected_filename():
    assert DB_PATH.endswith("project_viability.db"), f"Nombre de BD inesperado: {DB_PATH}"


def test_matrix_db_path_ends_with_expected_filename():
    assert MATRIX_DB_PATH.endswith("projects.db"), f"Nombre de BD inesperado: {MATRIX_DB_PATH}"
```

- [ ] **Step 2: Ejecutar tests para verificar que fallan**

```
.venv\Scripts\pytest tests/unit/test_constants.py -v
```

Expected: `ImportError` — el módulo no existe aún.

- [ ] **Step 3: Crear `config/constants.py`**

```python
# config/constants.py
"""Constantes globales de la aplicación. Única fuente de verdad para rutas y defaults."""
from pathlib import Path

# Root del proyecto (2 niveles arriba de config/)
_ROOT = Path(__file__).resolve().parent.parent

DB_PATH = str(_ROOT / "project_viability.db")
MATRIX_DB_PATH = str(_ROOT / "data" / "projects.db")
DEFAULT_AUTHOR = "Sistema"
```

- [ ] **Step 4: Ejecutar tests**

```
.venv\Scripts\pytest tests/unit/test_constants.py -v
```

Expected: 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add config/constants.py tests/unit/test_constants.py
git commit -m "feat: add config/constants.py with centralized DB_PATH and DEFAULT_AUTHOR"
```

---

## Task 2: Reemplazar `"project_viability.db"` en archivos de `infra/`

**Files:**
- Modify: `infra/db_migrations.py`
- Modify: `infra/db/connection.py`
- Modify: `infra/db/repositories/project_repo.py`
- Modify: `infra/db/repositories/evaluation_repo.py`
- Modify: `infra/db/repositories/notes_repo.py`

Para cada archivo:

- [ ] **Step 1: Lee cada archivo y encuentra la línea que define `DB_PATH = "project_viability.db"` o similar**

```
grep -n "project_viability.db" infra/db_migrations.py infra/db/connection.py infra/db/repositories/project_repo.py infra/db/repositories/evaluation_repo.py infra/db/repositories/notes_repo.py
```

- [ ] **Step 2: En cada archivo, reemplaza la definición local por el import centralizado**

Elimina la línea que define la constante local (ej: `DB_PATH = "project_viability.db"`) y agrega en los imports:

```python
from config.constants import DB_PATH
```

Si el archivo usaba `DB_PATH` como variable local con el mismo string, el resto del código no cambia — solo cambia la definición.

- [ ] **Step 3: Verificar que los módulos importan correctamente**

```
python -c "from infra.db_migrations import ensure_projects_schema; print('OK')"
python -c "from infra.db.connection import get_conn; print('OK')"
python -c "from infra.db.repositories.project_repo import ProjectRepository; print('OK')"
```

Expected: `OK` en los tres.

- [ ] **Step 4: Ejecutar tests de integración**

```
.venv\Scripts\pytest tests/integration/ -v
```

Expected: todos PASS.

- [ ] **Step 5: Commit**

```bash
git add infra/db_migrations.py infra/db/connection.py infra/db/repositories/project_repo.py infra/db/repositories/evaluation_repo.py infra/db/repositories/notes_repo.py
git commit -m "refactor: replace hardcoded 'project_viability.db' string in infra/ with config.constants.DB_PATH"
```

---

## Task 3: Reemplazar `"project_viability.db"` en `domain/` y `ui/`

**Files:**
- Modify: `domain/services/viability_service.py`
- Modify: `domain/services/seguimiento_operativo_service.py`
- Modify: `ui/tabs/shared.py`
- Modify: `ui/use_case_matrix.py`
- Modify: `ui/state.py`

- [ ] **Step 1: Buscar todas las ocurrencias restantes**

```
grep -rn "project_viability.db\|\"Xiomy\"" domain/ ui/
```

- [ ] **Step 2: Reemplazar `"project_viability.db"` por import en cada archivo encontrado**

Mismo patrón que Task 2: eliminar definición local, agregar `from config.constants import DB_PATH`.

Para `ui/tabs/shared.py` también importar `MATRIX_DB_PATH` si usa `"data/projects.db"`:
```python
from config.constants import DB_PATH, MATRIX_DB_PATH
```

- [ ] **Step 3: Reemplazar `"Xiomy"` en `ui/state.py`**

Busca la línea con `"Xiomy"` (línea ~31):
```python
return str(st.session_state.get("author", st.session_state.get("current_user", "Xiomy")))
```

Reemplaza por:
```python
from config.constants import DEFAULT_AUTHOR
# ...
return str(st.session_state.get("author", st.session_state.get("current_user", DEFAULT_AUTHOR)))
```

- [ ] **Step 4: Verificar imports de la app**

```
python -c "import sys; sys.path.insert(0,'.'); from ui.tabs.shared import t; print('OK')"
python -c "import sys; sys.path.insert(0,'.'); from ui.state import init_state; print('OK')"
```

Expected: `OK` en ambos.

- [ ] **Step 5: Verificar que no queda ninguna ocurrencia hardcodeada**

```
grep -rn "project_viability.db" domain/ ui/ infra/
```

Expected: sin resultados (o solo en comments/docs).

- [ ] **Step 6: Commit**

```bash
git add domain/services/viability_service.py domain/services/seguimiento_operativo_service.py ui/tabs/shared.py ui/use_case_matrix.py ui/state.py
git commit -m "refactor: replace hardcoded DB paths and 'Xiomy' default with config.constants"
```

---

## Task 4: Eliminar scoring duplicado en `planning.py`

**Files:**
- Modify: `ui/tabs/planning.py` (eliminar `_impact_points`, `_risk_points`, `_complexity_points`)

- [ ] **Step 1: Verificar que las funciones en `score_engine.py` son equivalentes**

Lee `domain/scoring/score_engine.py` líneas ~34-56 y `ui/tabs/planning.py` líneas ~118-137. Confirma que la lógica es idéntica.

- [ ] **Step 2: Buscar dónde se usan las funciones en `planning.py`**

```
grep -n "_impact_points\|_risk_points\|_complexity_points\|calculate_average_hourly_rate" ui/tabs/planning.py
```

- [ ] **Step 3: Reemplazar en `planning.py` el uso de funciones locales por las de `score_engine`**

Agrega el import al inicio de `planning.py`:
```python
from domain.scoring.score_engine import viability_component_scores
```

Elimina las definiciones locales de `_impact_points`, `_risk_points`, `_complexity_points` de `planning.py`.

Reemplaza las llamadas locales por llamadas a `viability_component_scores` del dominio. Por ejemplo, si `planning.py` tenía:
```python
score = _impact_points(tr) + _risk_points(risk) + _complexity_points(complexity)
```
Cambiar a:
```python
components = viability_component_scores(tr, risk, complexity)
score = components["impact"] + components["risk"] + components["complexity"]
```

(Ajustar nombres de parámetros según la firma real de `viability_component_scores` en `score_engine.py`.)

- [ ] **Step 4: Ejecutar todos los tests**

```
.venv\Scripts\pytest tests/ -v
```

Expected: todos PASS.

- [ ] **Step 5: Commit**

```bash
git add ui/tabs/planning.py
git commit -m "refactor: remove scoring logic duplicated in planning.py, use domain/scoring/score_engine"
```

---

## Self-Review

### Cobertura del reporte arquitectural

| Problema | Task |
|---|---|
| B1: Scoring duplicado en `planning.py` y `score_engine.py` | Task 4 |
| B2: `"project_viability.db"` en 8+ archivos | Tasks 2 y 3 |
| C1: `"Xiomy"` hardcodeado en `state.py` | Task 3 |

### Verificación final

```bash
# No debe quedar ningún string hardcodeado de BD
grep -rn '"project_viability.db"' . --include="*.py" --exclude-dir=".venv"

# No debe quedar el nombre personal
grep -rn '"Xiomy"' . --include="*.py" --exclude-dir=".venv"

# No debe quedar scoring duplicado
grep -n "_impact_points\|_risk_points\|_complexity_points" ui/tabs/planning.py
```

Expected: sin resultados en los tres.
