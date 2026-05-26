# Fix Duplicate-Key PostgreSQL + Autor Dinámico — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Corregir los errores `duplicate key` en `project_notes_pkey` y `project_evaluations_pkey` en Supabase, y hacer que el campo "Autor" en Captura rápida se auto-rellene con el nombre del usuario logueado (buscado en `project_members`).

**Architecture:** (1) `fix_pg_sequences()` sincroniza secuencias SERIAL de PostgreSQL con `MAX(id)` actual — corre en cada startup vía `ensure_all_operational_schema`. (2) `evaluation_repo.py` se migra a `PLACEHOLDER` y manejo de ID compatible con psycopg2. (3) Al login se deriva el nombre del email y se guarda en `session_state["current_user"]`; al renderizar Captura rápida se busca ese nombre en `project_members` con un helper testeable.

**Tech Stack:** Python 3.11, Streamlit, psycopg2 (cloud), sqlite3 (local), pytest.

---

## File Map

| Archivo | Acción |
|---|---|
| `infra/db_migrations.py` | Agregar `fix_pg_sequences()` + llamarla en `ensure_all_operational_schema` |
| `infra/db/repositories/evaluation_repo.py` | `?` → `PLACEHOLDER`, `lastrowid` → dual-path, `datetime()` → dual-path |
| `ui/login.py` | Agregar `_derive_display_name()`, setear `current_user` en `render_login()` |
| `ui/tabs/seguimiento_operativo.py` | Extraer `_resolve_default_author()`, usarla en `_render_capture_tab` |
| `ui/state.py` | Actualizar fallback en `get_author_default()` |
| `tests/unit/test_pg_sequences.py` | Nuevo — tests para `fix_pg_sequences` |
| `tests/ui/test_login.py` | Agregar tests para `_derive_display_name` |
| `tests/unit/test_author_resolution.py` | Nuevo — tests para `_resolve_default_author` |
| `tests/integration/test_repositories.py` | Verificar regresión en `evaluation_repo` (test existente) |

---

## Task 1: Fix `evaluation_repo.py` — PLACEHOLDER y cloud-compatible lastrowid

**Files:**
- Modify: `infra/db/repositories/evaluation_repo.py`
- Test: `tests/integration/test_repositories.py` (test existente como regresión)

El archivo actual usa `?` hardcodeado (SQLite) y `cur.lastrowid` que psycopg2 no soporta. En cloud, `PLACEHOLDER = "%s"` y el ID se obtiene con `SELECT MAX(evaluation_id)` o `SELECT last_insert_rowid()` según plataforma.

- [ ] **Step 1: Correr el test existente para tener línea base verde**

```bash
cd "C:\Users\ttMonroyX\OneDrive - Kantar\Documents\Project Managment\ReportesAdhoc\EvaluadorDeProyectos\Repositorio Evaluador\.claude\worktrees\elastic-bassi-1dce1c"
python -m pytest tests/integration/test_repositories.py::test_evaluation_repo_insert_and_list -v
```

Expected: PASS (con SQLite, `?` funciona localmente — el test sirve de regresión).

- [ ] **Step 2: Reemplazar todo el contenido de `evaluation_repo.py`**

```python
"""Repositorio de snapshots de evaluaciones."""

from __future__ import annotations

import json
from typing import Any

from infra.db.adapter import IS_CLOUD, PLACEHOLDER
from infra.db.connection import get_sqlite_conn


class EvaluationRepository:
    def __init__(self, db_path: str = "project_viability.db") -> None:
        self.db_path = db_path

    def insert_snapshot(
        self,
        project_id: str,
        action: str,
        status_after: str,
        calc_results: dict[str, Any],
        inputs_json: dict[str, Any],
        created_by: str,
    ) -> int:
        placeholders = ", ".join([PLACEHOLDER] * 14)
        with get_sqlite_conn(self.db_path) as conn:
            conn.execute(
                f"""
                INSERT INTO project_evaluations (
                    project_id, created_by, action, status_after,
                    score_total, score_impact, score_risk, score_complexity,
                    monthly_savings, annual_savings, payback_period_months, roi_first_year,
                    hours_saved_per_month, inputs_json
                ) VALUES ({placeholders})
                """,
                (
                    project_id,
                    (created_by or "").strip(),
                    action,
                    status_after,
                    float(calc_results.get("viability_score", 0) or 0),
                    float(calc_results.get("score_impact", 0) or 0),
                    float(calc_results.get("score_risk", 0) or 0),
                    float(calc_results.get("score_complexity", 0) or 0),
                    float(calc_results.get("monthly_savings", 0) or 0),
                    float(calc_results.get("annual_savings", 0) or 0),
                    calc_results.get("payback_period_months"),
                    float(calc_results.get("roi_first_year", 0) or 0),
                    float(calc_results.get("hours_saved_per_month", 0) or 0),
                    json.dumps(inputs_json, ensure_ascii=False),
                ),
            )
            if IS_CLOUD:
                row = conn.execute(
                    "SELECT MAX(evaluation_id) AS last_id FROM project_evaluations"
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT last_insert_rowid() AS last_id"
                ).fetchone()
            conn.commit()
            return int(row["last_id"] or 0) if row else 0

    def list_snapshots(self, project_id: str) -> list[dict[str, Any]]:
        order_expr = "created_at" if IS_CLOUD else "datetime(created_at)"
        with get_sqlite_conn(self.db_path) as conn:
            rows = conn.execute(
                f"""
                SELECT *
                FROM project_evaluations
                WHERE project_id = {PLACEHOLDER}
                ORDER BY {order_expr} DESC, evaluation_id DESC
                """,
                (project_id,),
            ).fetchall()
            return [dict(r) for r in rows]
```

- [ ] **Step 3: Correr test de regresión**

```bash
python -m pytest tests/integration/test_repositories.py::test_evaluation_repo_insert_and_list -v
```

Expected: PASS — mismo comportamiento, ahora con `PLACEHOLDER` correcto.

- [ ] **Step 4: Commit**

```bash
git add infra/db/repositories/evaluation_repo.py
git commit -m "fix: evaluation_repo — PLACEHOLDER y lastrowid compatible con PostgreSQL"
```

---

## Task 2: Agregar `fix_pg_sequences()` en `db_migrations.py`

**Files:**
- Modify: `infra/db_migrations.py`
- Create: `tests/unit/test_pg_sequences.py`

La función llama `setval(pg_get_serial_sequence(...), MAX(id))` para cada tabla. Es idempotente: si la secuencia ya está correcta, `setval` la deja igual.

- [ ] **Step 1: Crear `tests/unit/test_pg_sequences.py` con tests que fallan**

```python
"""Tests para fix_pg_sequences en db_migrations."""


def test_fix_pg_sequences_skips_when_not_cloud(monkeypatch):
    """Cuando IS_CLOUD=False la función no ejecuta nada."""
    import infra.db_migrations as mig
    monkeypatch.setattr(mig, "IS_CLOUD", False)

    executed = []

    class _Conn:
        def execute(self, sql, params=()):
            executed.append(sql)
        def commit(self):
            pass

    mig.fix_pg_sequences(_Conn())
    assert executed == [], "No debe ejecutar SQL en modo SQLite"


def test_fix_pg_sequences_calls_setval_for_three_tables(monkeypatch):
    """Cuando IS_CLOUD=True llama setval para las tres tablas."""
    import infra.db_migrations as mig
    monkeypatch.setattr(mig, "IS_CLOUD", True)

    executed = []

    class _Conn:
        def execute(self, sql, params=()):
            executed.append(sql)
            return self
        def fetchone(self):
            return None
        def commit(self):
            pass

    mig.fix_pg_sequences(_Conn())

    assert any("project_notes" in s for s in executed), "Debe sincronizar project_notes"
    assert any("project_evaluations" in s for s in executed), "Debe sincronizar project_evaluations"
    assert any("project_members" in s for s in executed), "Debe sincronizar project_members"


def test_fix_pg_sequences_tolerates_table_error(monkeypatch):
    """Si una tabla lanza excepción, las demás siguen ejecutándose."""
    import infra.db_migrations as mig
    monkeypatch.setattr(mig, "IS_CLOUD", True)

    call_count = [0]

    class _Conn:
        def execute(self, sql, params=()):
            call_count[0] += 1
            if "project_notes" in sql:
                raise Exception("tabla no existe")
            return self
        def fetchone(self):
            return None
        def commit(self):
            pass

    # No debe propagar la excepción
    mig.fix_pg_sequences(_Conn())
    # project_evaluations y project_members deben haberse intentado
    assert call_count[0] >= 2


def test_ensure_all_operational_schema_calls_fix_sequences_in_cloud(monkeypatch):
    """ensure_all_operational_schema llama fix_pg_sequences cuando IS_CLOUD=True."""
    import infra.db_migrations as mig
    monkeypatch.setattr(mig, "IS_CLOUD", True)

    called = []

    def _fake_fix(conn):
        called.append(True)

    def _fake_ensure_members(conn):
        pass

    monkeypatch.setattr(mig, "fix_pg_sequences", _fake_fix)
    monkeypatch.setattr(mig, "ensure_members_schema", _fake_ensure_members)

    class _Conn:
        pass

    mig.ensure_all_operational_schema(_Conn())
    assert called == [True], "fix_pg_sequences debe llamarse en modo cloud"
```

- [ ] **Step 2: Correr tests para verificar que fallan**

```bash
python -m pytest tests/unit/test_pg_sequences.py -v
```

Expected: `AttributeError: module 'infra.db_migrations' has no attribute 'fix_pg_sequences'` en los 4 tests.

- [ ] **Step 3: Agregar `fix_pg_sequences` en `infra/db_migrations.py`**

Agregar la función después de `ensure_members_schema` (al final del bloque de funciones, antes de `ensure_all_operational_schema`):

```python
def fix_pg_sequences(conn) -> None:
    """Sincroniza secuencias SERIAL de PostgreSQL con el MAX actual de cada tabla.

    Solo corre en cloud (IS_CLOUD=True). Idempotente — no daña datos existentes.
    Silencia errores por tabla para que una tabla faltante no bloquee las demás.
    """
    if not IS_CLOUD:
        return
    pairs = [
        ("project_notes", "note_id"),
        ("project_evaluations", "evaluation_id"),
        ("project_members", "id"),
    ]
    for table, col in pairs:
        try:
            conn.execute(
                "SELECT setval("
                f"  pg_get_serial_sequence('{table}', '{col}'),"
                f"  COALESCE((SELECT MAX({col}) FROM {table}), 1)"
                ")"
            )
        except Exception:
            pass  # tabla puede no existir en esta sesión
    conn.commit()
```

- [ ] **Step 4: Actualizar `ensure_all_operational_schema` para llamar `fix_pg_sequences`**

Localizar el bloque `if IS_CLOUD:` en `ensure_all_operational_schema` (al final del archivo) y modificarlo:

```python
def ensure_all_operational_schema(conn) -> None:
    """Atajo para asegurar esquemas de projects/evaluations/notes."""
    from infra.db.adapter import IS_CLOUD

    if IS_CLOUD:
        # En cloud solo creamos project_members si no existe (el resto ya está en Supabase)
        ensure_members_schema(conn)
        fix_pg_sequences(conn)  # sincroniza secuencias SERIAL tras cualquier migración de datos
        return
    ensure_projects_schema(conn)
    ensure_evaluations_schema(conn)
    ensure_notes_schema(conn)
    ensure_members_schema(conn)
```

- [ ] **Step 5: Correr todos los tests de la suite**

```bash
python -m pytest tests/unit/test_pg_sequences.py tests/integration/test_repositories.py -v
```

Expected: todos PASS.

- [ ] **Step 6: Commit**

```bash
git add infra/db_migrations.py tests/unit/test_pg_sequences.py
git commit -m "fix: fix_pg_sequences sincroniza secuencias SERIAL de PostgreSQL en startup"
```

---

## Task 3: Agregar `_derive_display_name()` en `login.py` y setear `current_user`

**Files:**
- Modify: `ui/login.py`
- Test: `tests/ui/test_login.py`

`_derive_display_name` parsea la parte local del email, separa por `.` o `_`, capitaliza cada parte. Resultado: `"carlos.montiel@..."` → `"Carlos Montiel"`. Se guarda en `session_state["current_user"]` al autenticarse.

- [ ] **Step 1: Agregar tests a `tests/ui/test_login.py`**

Añadir al final del archivo:

```python
def test_derive_display_name_dot_separated():
    from ui.login import _derive_display_name

    assert _derive_display_name("carlos.montiel@wp.numerator.com") == "Carlos Montiel"


def test_derive_display_name_xiomara():
    from ui.login import _derive_display_name

    assert _derive_display_name("xiomara.monroy@wp.numerator.com") == "Xiomara Monroy"


def test_derive_display_name_single_word():
    from ui.login import _derive_display_name

    assert _derive_display_name("admin@example.com") == "Admin"


def test_derive_display_name_underscore_separator():
    from ui.login import _derive_display_name

    assert _derive_display_name("juan_perez@example.com") == "Juan Perez"


def test_derive_display_name_mixed_separators():
    from ui.login import _derive_display_name

    assert _derive_display_name("ana.garcia_lopez@example.com") == "Ana Garcia Lopez"
```

- [ ] **Step 2: Correr para confirmar que fallan**

```bash
python -m pytest tests/ui/test_login.py::test_derive_display_name_dot_separated -v
```

Expected: `ImportError: cannot import name '_derive_display_name' from 'ui.login'`.

- [ ] **Step 3: Agregar `_derive_display_name` en `ui/login.py`**

Agregar la función justo después de los imports (antes de `verify_password`):

```python
def _derive_display_name(email: str) -> str:
    """Deriva nombre para mostrar del email del usuario.

    Ejemplos:
        'carlos.montiel@wp.numerator.com' → 'Carlos Montiel'
        'xiomara.monroy@wp.numerator.com' → 'Xiomara Monroy'
        'admin@example.com'              → 'Admin'
    """
    local = email.split("@")[0]
    parts = local.replace("_", " ").replace(".", " ").split()
    return " ".join(p.capitalize() for p in parts)
```

- [ ] **Step 4: Actualizar `render_login()` para setear `current_user`**

Localizar el bloque `if submitted:` dentro de `render_login()`. El bloque actual es:

```python
        if user and user["is_active"] and verify_password(password, user["password_hash"]):
            st.session_state["authenticated"] = True
            st.session_state["user_email"] = user["email"]
            st.rerun()
```

Reemplazar por:

```python
        if user and user["is_active"] and verify_password(password, user["password_hash"]):
            st.session_state["authenticated"] = True
            st.session_state["user_email"] = user["email"]
            st.session_state["current_user"] = _derive_display_name(user["email"])
            st.rerun()
```

- [ ] **Step 5: Correr todos los tests de login**

```bash
python -m pytest tests/ui/test_login.py -v
```

Expected: todos PASS (5 tests de `_derive_display_name` + 3 existentes de `verify_password`).

- [ ] **Step 6: Commit**

```bash
git add ui/login.py tests/ui/test_login.py
git commit -m "feat: login deriva current_user del email para autor dinamico en Captura rapida"
```

---

## Task 4: Extraer `_resolve_default_author()` y actualizar `default_author` en `seguimiento_operativo.py`

**Files:**
- Modify: `ui/tabs/seguimiento_operativo.py`
- Create: `tests/unit/test_author_resolution.py`

Se extrae la lógica de resolución a `_resolve_default_author(candidate, all_members, fallback)` — función pura, testeable. Luego se reemplaza la línea de `default_author` en `_render_capture_tab` para usar la función y buscar en `project_members`.

- [ ] **Step 1: Crear `tests/unit/test_author_resolution.py`**

```python
"""Tests para _resolve_default_author en seguimiento_operativo."""


def test_resolve_finds_exact_match():
    from ui.tabs.seguimiento_operativo import _resolve_default_author

    members = ["Carlos Montiel", "Xiomara Monroy"]
    assert _resolve_default_author("Carlos Montiel", members) == "Carlos Montiel"


def test_resolve_is_case_insensitive():
    from ui.tabs.seguimiento_operativo import _resolve_default_author

    members = ["Xiomara Monroy"]
    assert _resolve_default_author("xiomara monroy", members) == "Xiomara Monroy"


def test_resolve_preserves_db_casing():
    from ui.tabs.seguimiento_operativo import _resolve_default_author

    # El miembro en BD tiene capitalización propia — se usa la de la BD
    members = ["CARLOS MONTIEL"]
    assert _resolve_default_author("carlos montiel", members) == "CARLOS MONTIEL"


def test_resolve_returns_candidate_when_not_in_members():
    from ui.tabs.seguimiento_operativo import _resolve_default_author

    members = ["Carlos Montiel"]
    assert _resolve_default_author("Nuevo Usuario", members) == "Nuevo Usuario"


def test_resolve_returns_fallback_when_candidate_is_empty():
    from ui.tabs.seguimiento_operativo import _resolve_default_author

    members = ["Carlos Montiel"]
    assert _resolve_default_author("", members) == "Xiomara Monroy"


def test_resolve_returns_fallback_when_candidate_is_whitespace():
    from ui.tabs.seguimiento_operativo import _resolve_default_author

    members = ["Carlos Montiel"]
    assert _resolve_default_author("   ", members) == "Xiomara Monroy"


def test_resolve_custom_fallback():
    from ui.tabs.seguimiento_operativo import _resolve_default_author

    assert _resolve_default_author("", [], fallback="Admin") == "Admin"
```

- [ ] **Step 2: Correr para confirmar que fallan**

```bash
python -m pytest tests/unit/test_author_resolution.py -v
```

Expected: `ImportError: cannot import name '_resolve_default_author' from 'ui.tabs.seguimiento_operativo'`.

- [ ] **Step 3: Agregar `_resolve_default_author()` en `ui/tabs/seguimiento_operativo.py`**

Agregar la función después de `_progress_badge` (línea ~894, antes de `get_executive_summary_df`):

```python
def _resolve_default_author(
    candidate: str,
    all_members: list[str],
    fallback: str = "Xiomara Monroy",
) -> str:
    """Resuelve el nombre de autor para Captura rápida.

    Busca `candidate` en `all_members` con comparación case-insensitive.
    Si hay match, devuelve el nombre exacto de la BD.
    Si no hay match y candidate no está vacío, devuelve candidate tal cual.
    Si candidate está vacío, devuelve fallback.
    """
    stripped = candidate.strip()
    if not stripped:
        return fallback
    lower = stripped.lower()
    for member in all_members:
        if member.lower() == lower:
            return member
    return stripped
```

- [ ] **Step 4: Correr tests unitarios de la función**

```bash
python -m pytest tests/unit/test_author_resolution.py -v
```

Expected: todos PASS.

- [ ] **Step 5: Actualizar `_render_capture_tab` para usar `_resolve_default_author`**

Localizar en `_render_capture_tab` (alrededor de la línea 1351) la línea:

```python
    default_author = str(st.session_state.get("author", st.session_state.get("current_user", "Xiomara Monroy")))
```

Reemplazar por:

```python
    _candidate = str(st.session_state.get("current_user", st.session_state.get("author", "")))
    _all_members = get_all_known_members(conn)
    default_author = _resolve_default_author(_candidate, _all_members)
```

- [ ] **Step 6: Correr suite completa para verificar no hay regresión**

```bash
python -m pytest tests/unit/ tests/integration/test_repositories.py tests/ui/test_login.py -v
```

Expected: todos PASS.

- [ ] **Step 7: Commit**

```bash
git add ui/tabs/seguimiento_operativo.py tests/unit/test_author_resolution.py
git commit -m "feat: autor dinamico en Captura rapida — busca nombre en project_members via session email"
```

---

## Task 5: Actualizar `get_author_default()` en `state.py` + commit de cierre

**Files:**
- Modify: `ui/state.py`

Alinear el fallback de `get_author_default()` con el resto del sistema (usa "Xiomara Monroy" en lugar de "Xiomy").

- [ ] **Step 1: Editar `ui/state.py`**

Localizar:

```python
def get_author_default() -> str:
    return str(st.session_state.get("author", st.session_state.get("current_user", "Xiomy")))
```

Reemplazar por:

```python
def get_author_default() -> str:
    return str(st.session_state.get("author", st.session_state.get("current_user", "Xiomara Monroy")))
```

- [ ] **Step 2: Correr suite completa final**

```bash
python -m pytest tests/ -v --tb=short
```

Expected: todos PASS. Anotar cualquier fallo para investigar antes de hacer push.

- [ ] **Step 3: Commit final**

```bash
git add ui/state.py
git commit -m "fix: get_author_default fallback consistente con Xiomara Monroy"
```

- [ ] **Step 4: Push de la rama**

```bash
git push origin claude/elastic-bassi-1dce1c
```

---

## Criterios de verificación final

Tras la implementación, verificar manualmente en SCC (cloud):

1. **Notas**: Ir a Bitácora → Captura rápida → guardar una nota → no debe aparecer `duplicate key` en `project_notes_pkey`.
2. **Evaluaciones**: Crear un nuevo proyecto en la hoja de viabilidad → guardar → no debe aparecer `duplicate key` en `project_evaluations_pkey`.
3. **Autor Xiomara**: Iniciar sesión como `xiomara.monroy@wp.numerator.com` → campo "Autor" debe mostrar `"Xiomara Monroy"`.
4. **Autor Carlos**: Iniciar sesión como `carlos.montiel@wp.numerator.com` → campo "Autor" debe mostrar `"Carlos Montiel"` (si está en `project_members`) o `"Carlos Montiel"` derivado del email.
5. **Idempotencia**: Recargar la app dos veces — no debe haber errores de `fix_pg_sequences`.
