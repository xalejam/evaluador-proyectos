# Effort Hours Tracking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Agregar registro obligatorio de horas de esfuerzo a todas las notas operativas, un tipo de nota post-cierre (`soporte_post_entrega`), scripts de backfill histórico via CSV, y un bloque "Tiempo real" en el dashboard.

**Architecture:** Se extiende el schema de `project_viability.db` con dos columnas nuevas (`effort_hours` en `project_notes`, `closed_at` en `projects`) usando las migraciones idempotentes ya existentes. La UI de Captura rápida en `ui/tabs/seguimiento_operativo.py` recibe un campo de horas obligatorio y una sección post-cierre condicional. El dashboard muestra métricas de horas con `st.metric()`.

**Tech Stack:** Python 3.11+, SQLite3, Streamlit, pytest. Sin dependencias nuevas.

---

## Mapa de archivos

| Archivo | Acción | Responsabilidad |
|---|---|---|
| `infra/db_migrations.py` | Modificar | Agregar `effort_hours` y `closed_at` vía `_add_column_if_missing`; actualizar `update_project_status` para grabar `closed_at` |
| `ui/tabs/seguimiento_operativo.py` | Modificar | Campo horas obligatorio en formulario; sección post-cierre; validación; bloque métricas dashboard |
| `scripts/export_notes_for_hours.py` | Crear | Exporta notas sin `effort_hours` a CSV |
| `scripts/import_notes_hours.py` | Crear | Importa CSV con horas; valida y actualiza BD |
| `tests/unit/test_effort_hours_migrations.py` | Crear | Tests de migraciones idempotentes |
| `tests/unit/test_effort_hours_import.py` | Crear | Tests de validación del script de importación |

---

## Task 1: Migraciones de schema

**Files:**
- Modify: `infra/db_migrations.py`
- Create: `tests/unit/test_effort_hours_migrations.py`

- [ ] **Step 1: Escribir los tests que verifican las nuevas columnas**

Crear `tests/unit/test_effort_hours_migrations.py`:

```python
import sqlite3
import pytest
from infra.db_migrations import ensure_projects_schema, ensure_notes_schema


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    yield c
    c.close()


def _columns(conn, table):
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def test_effort_hours_added_to_project_notes(conn):
    ensure_notes_schema(conn)
    assert "effort_hours" in _columns(conn, "project_notes")


def test_closed_at_added_to_projects(conn):
    ensure_projects_schema(conn)
    assert "closed_at" in _columns(conn, "projects")


def test_migrations_are_idempotent(conn):
    ensure_projects_schema(conn)
    ensure_notes_schema(conn)
    # segunda ejecucion no debe lanzar excepcion
    ensure_projects_schema(conn)
    ensure_notes_schema(conn)
    assert "effort_hours" in _columns(conn, "project_notes")
    assert "closed_at" in _columns(conn, "projects")


def test_effort_hours_is_nullable(conn):
    ensure_notes_schema(conn)
    conn.execute(
        "INSERT INTO project_notes (project_id, note_text, note_type, author) VALUES (?,?,?,?)",
        ("P1", "texto", "general", "Xiomara"),
    )
    row = conn.execute("SELECT effort_hours FROM project_notes LIMIT 1").fetchone()
    assert row["effort_hours"] is None
```

- [ ] **Step 2: Correr tests — deben fallar**

```bash
cd "c:\Users\ttMonroyX\OneDrive - Kantar\Documents\Project Managment\ReportesAdhoc\EvaluadorDeProyectos\Repositorio Evaluador"
.venv\Scripts\python -m pytest tests/unit/test_effort_hours_migrations.py -v
```

Esperado: FAIL — `effort_hours` y `closed_at` no existen aún.

- [ ] **Step 3: Agregar columnas en `infra/db_migrations.py`**

En `ensure_notes_schema`, después de la línea que agrega `estimated_end_date`:

```python
    _add_column_if_missing(conn, "project_notes", "effort_hours REAL")
```

En `ensure_projects_schema`, al final de la función (después del bloque `updated_at`):

```python
    _add_column_if_missing(conn, "projects", "closed_at TEXT")
```

- [ ] **Step 4: Correr tests — deben pasar**

```bash
.venv\Scripts\python -m pytest tests/unit/test_effort_hours_migrations.py -v
```

Esperado: 4 PASSED.

- [ ] **Step 5: Aplicar migración a la BD real**

```bash
.venv\Scripts\python -c "
import sqlite3
from infra.db_migrations import ensure_projects_schema, ensure_notes_schema
conn = sqlite3.connect('project_viability.db')
ensure_projects_schema(conn)
ensure_notes_schema(conn)
conn.close()
print('OK')
"
```

Esperado: `OK` sin errores.

- [ ] **Step 6: Commit**

```bash
git add infra/db_migrations.py tests/unit/test_effort_hours_migrations.py
git commit -m "feat: add effort_hours to project_notes and closed_at to projects schema"
```

---

## Task 2: Trigger `closed_at` al cambiar status a `implemented`

**Files:**
- Modify: `infra/db_migrations.py` (función `update_project_status`)
- Modify: `tests/unit/test_effort_hours_migrations.py`

- [ ] **Step 1: Agregar test para el trigger**

Añadir al final de `tests/unit/test_effort_hours_migrations.py`:

```python
from infra.db_migrations import update_project_status


def test_closed_at_set_when_status_implemented(conn):
    ensure_projects_schema(conn)
    conn.execute(
        "INSERT INTO projects (id, project_id, name, status) VALUES (?,?,?,?)",
        ("P1", "P1", "Proyecto Test", "executing"),
    )
    conn.commit()
    update_project_status(conn, "P1", "implemented")
    row = conn.execute("SELECT closed_at, status FROM projects WHERE id='P1'").fetchone()
    assert row["status"] == "implemented"
    assert row["closed_at"] is not None


def test_closed_at_not_overwritten_on_second_implemented(conn):
    ensure_projects_schema(conn)
    conn.execute(
        "INSERT INTO projects (id, project_id, name, status, closed_at) VALUES (?,?,?,?,?)",
        ("P2", "P2", "Proyecto 2", "implemented", "2026-03-01 10:00:00"),
    )
    conn.commit()
    update_project_status(conn, "P2", "implemented")
    row = conn.execute("SELECT closed_at FROM projects WHERE id='P2'").fetchone()
    assert row["closed_at"] == "2026-03-01 10:00:00"
```

- [ ] **Step 2: Correr tests nuevos — deben fallar**

```bash
.venv\Scripts\python -m pytest tests/unit/test_effort_hours_migrations.py::test_closed_at_set_when_status_implemented tests/unit/test_effort_hours_migrations.py::test_closed_at_not_overwritten_on_second_implemented -v
```

Esperado: FAIL.

- [ ] **Step 3: Actualizar `update_project_status` en `infra/db_migrations.py`**

Reemplazar la función actual:

```python
def update_project_status(conn: sqlite3.Connection, project_id: str, status: str) -> None:
    conn.execute(
        "UPDATE projects SET status = ?, updated_at = datetime('now') WHERE id = ? OR project_id = ?",
        (status.strip(), project_id.strip(), project_id.strip()),
    )
    if status.strip() == "implemented":
        conn.execute(
            """
            UPDATE projects
            SET closed_at = datetime('now')
            WHERE (id = ? OR project_id = ?)
              AND (closed_at IS NULL OR closed_at = '')
            """,
            (project_id.strip(), project_id.strip()),
        )
    conn.commit()
```

- [ ] **Step 4: Correr todos los tests de migraciones**

```bash
.venv\Scripts\python -m pytest tests/unit/test_effort_hours_migrations.py -v
```

Esperado: 6 PASSED.

- [ ] **Step 5: Commit**

```bash
git add infra/db_migrations.py tests/unit/test_effort_hours_migrations.py
git commit -m "feat: auto-set closed_at when project status changes to implemented"
```

---

## Task 3: Scripts de backfill — export e import CSV

**Files:**
- Create: `scripts/export_notes_for_hours.py`
- Create: `scripts/import_notes_hours.py`
- Create: `tests/unit/test_effort_hours_import.py`

- [ ] **Step 1: Escribir tests de validación del import**

Crear `tests/unit/test_effort_hours_import.py`:

```python
import csv
import io
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from infra.db_migrations import ensure_notes_schema


@pytest.fixture
def db_with_notes(tmp_path):
    db_file = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    ensure_notes_schema(conn)
    conn.execute(
        "INSERT INTO project_notes (note_id, project_id, note_text, note_type, author) VALUES (1,'P1','texto','general','Xiomara')"
    )
    conn.execute(
        "INSERT INTO project_notes (note_id, project_id, note_text, note_type, author) VALUES (2,'P1','texto2','proximo_paso','Xiomara')"
    )
    conn.commit()
    conn.close()
    return db_file


def _run_import(db_path, rows):
    """Helper: escribe CSV temporal y llama a la logica de importacion."""
    from scripts.import_notes_hours import import_hours

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["note_id", "project_id", "note_type", "note_title", "created_at", "note_text", "effort_hours"])
    writer.writeheader()
    for r in rows:
        writer.writerow(r)
    buf.seek(0)
    return import_hours(str(db_path), buf)


def test_valid_import_updates_hours(db_with_notes):
    result = _run_import(db_with_notes, [
        {"note_id": 1, "project_id": "P1", "note_type": "general", "note_title": "", "created_at": "", "note_text": "", "effort_hours": 4.5},
        {"note_id": 2, "project_id": "P1", "note_type": "proximo_paso", "note_title": "", "created_at": "", "note_text": "", "effort_hours": 2.0},
    ])
    assert result["updated"] == 2
    assert result["rejected"] == 0

    conn = sqlite3.connect(str(db_with_notes))
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT effort_hours FROM project_notes WHERE note_id=1").fetchone()
    assert row["effort_hours"] == 4.5
    conn.close()


def test_zero_hours_rejected(db_with_notes):
    result = _run_import(db_with_notes, [
        {"note_id": 1, "project_id": "P1", "note_type": "general", "note_title": "", "created_at": "", "note_text": "", "effort_hours": 0},
    ])
    assert result["rejected"] == 1
    assert len(result["rejected_rows"]) == 1


def test_empty_hours_rejected(db_with_notes):
    result = _run_import(db_with_notes, [
        {"note_id": 1, "project_id": "P1", "note_type": "general", "note_title": "", "created_at": "", "note_text": "", "effort_hours": ""},
    ])
    assert result["rejected"] == 1


def test_nonexistent_note_id_rejected(db_with_notes):
    result = _run_import(db_with_notes, [
        {"note_id": 999, "project_id": "P1", "note_type": "general", "note_title": "", "created_at": "", "note_text": "", "effort_hours": 3.0},
    ])
    assert result["rejected"] == 1


def test_negative_hours_rejected(db_with_notes):
    result = _run_import(db_with_notes, [
        {"note_id": 1, "project_id": "P1", "note_type": "general", "note_title": "", "created_at": "", "note_text": "", "effort_hours": -1.5},
    ])
    assert result["rejected"] == 1
```

- [ ] **Step 2: Correr tests — deben fallar**

```bash
.venv\Scripts\python -m pytest tests/unit/test_effort_hours_import.py -v
```

Esperado: FAIL — los scripts no existen aún.

- [ ] **Step 3: Crear `scripts/export_notes_for_hours.py`**

```python
#!/usr/bin/env python3
"""Exporta notas sin effort_hours a CSV para backfill manual."""

import csv
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "project_viability.db"
OUTPUT_CSV = ROOT / "notas_horas.csv"

FIELDS = ["note_id", "project_id", "note_type", "note_title", "created_at", "note_text", "effort_hours"]


def export_notes(db_path: str = str(DB_PATH), output_path: str = str(OUTPUT_CSV)) -> int:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT note_id, project_id, note_type, note_title, created_at, note_text
        FROM project_notes
        WHERE effort_hours IS NULL
        ORDER BY project_id, created_at
        """
    ).fetchall()
    conn.close()

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for r in rows:
            writer.writerow({**dict(r), "effort_hours": ""})

    print(f"Exportadas {len(rows)} notas a {output_path}")
    return len(rows)


if __name__ == "__main__":
    export_notes()
```

- [ ] **Step 4: Crear `scripts/import_notes_hours.py`**

```python
#!/usr/bin/env python3
"""Importa horas de esfuerzo desde CSV a project_notes."""

import csv
import io
import sqlite3
import sys
from pathlib import Path
from typing import Union

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "project_viability.db"


def import_hours(db_path: str, source: Union[str, io.StringIO]) -> dict:
    """
    Lee CSV con columnas [note_id, effort_hours] y actualiza project_notes.
    Retorna dict con claves: updated (int), rejected (int), rejected_rows (list).
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    existing_ids = {
        r[0] for r in conn.execute("SELECT note_id FROM project_notes").fetchall()
    }

    if isinstance(source, str):
        f = open(source, newline="", encoding="utf-8")
        close_file = True
    else:
        f = source
        close_file = False

    reader = csv.DictReader(f)
    updated = 0
    rejected = 0
    rejected_rows = []

    for row in reader:
        note_id_raw = str(row.get("note_id", "")).strip()
        hours_raw = str(row.get("effort_hours", "")).strip()

        # Validar note_id
        try:
            note_id = int(note_id_raw)
        except ValueError:
            rejected += 1
            rejected_rows.append({"note_id": note_id_raw, "reason": "note_id no es entero"})
            continue

        if note_id not in existing_ids:
            rejected += 1
            rejected_rows.append({"note_id": note_id, "reason": "note_id no existe en BD"})
            continue

        # Validar effort_hours
        if not hours_raw:
            rejected += 1
            rejected_rows.append({"note_id": note_id, "reason": "effort_hours vacío"})
            continue

        try:
            effort_hours = float(hours_raw)
        except ValueError:
            rejected += 1
            rejected_rows.append({"note_id": note_id, "reason": f"effort_hours no es número: {hours_raw!r}"})
            continue

        if effort_hours <= 0:
            rejected += 1
            rejected_rows.append({"note_id": note_id, "reason": f"effort_hours debe ser > 0 (fue {effort_hours})"})
            continue

        conn.execute(
            "UPDATE project_notes SET effort_hours = ? WHERE note_id = ?",
            (effort_hours, note_id),
        )
        updated += 1

    conn.commit()
    conn.close()
    if close_file:
        f.close()

    return {"updated": updated, "rejected": rejected, "rejected_rows": rejected_rows}


def _print_report(result: dict) -> None:
    print(f"Actualizadas: {result['updated']:>5} notas")
    print(f"Rechazadas:   {result['rejected']:>5} notas")
    if result["rejected_rows"]:
        for r in result["rejected_rows"]:
            print(f"  → note_id {r['note_id']}: {r['reason']}")


if __name__ == "__main__":
    csv_path = sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "notas_horas.csv")
    result = import_hours(str(DB_PATH), csv_path)
    _print_report(result)
    if result["rejected"] > 0:
        sys.exit(1)
```

- [ ] **Step 5: Correr todos los tests del import**

```bash
.venv\Scripts\python -m pytest tests/unit/test_effort_hours_import.py -v
```

Esperado: 5 PASSED.

- [ ] **Step 6: Commit**

```bash
git add scripts/export_notes_for_hours.py scripts/import_notes_hours.py tests/unit/test_effort_hours_import.py
git commit -m "feat: add CSV backfill scripts for effort_hours (export + import with validation)"
```

---

## Task 4: Campo de horas obligatorio en Captura rápida

**Files:**
- Modify: `ui/tabs/seguimiento_operativo.py`

Los cambios son todos en la función que contiene el `st.form(key=f"ops_capture_form_...")` — aproximadamente líneas 1074–1197.

- [ ] **Step 1: Agregar constante `POST_CLOSURE_TYPE` al bloque de constantes**

En `ui/tabs/seguimiento_operativo.py`, después de la línea `END_MARKER = "/end"` (línea ~38):

```python
POST_CLOSURE_TYPE = "soporte_post_entrega"
```

- [ ] **Step 2: Agregar el input de horas dentro del formulario existente**

Después del bloque `estimated_end_date_input` (después de la línea `st.caption(f"{t('ops_progress_suggested')}...`)`) y antes de `general = st.text_area(...)`, agregar:

```python
        effort_hours_input = st.number_input(
            "Horas invertidas esta semana",
            min_value=0.0,
            max_value=80.0,
            value=0.0,
            step=0.5,
            key=f"ops_effort_hours_{selected_project.project_id}",
        )
```

- [ ] **Step 3: Agregar validación de horas en el bloque `if submitted:`**

En el bloque `if submitted:`, después de la validación de `loop_url_input` y antes de `entry_group_id = uuid.uuid4().hex`, agregar:

```python
        elif effort_hours_input <= 0:
            st.error("Las horas invertidas son obligatorias y deben ser mayores a 0.")
```

Y envolver el resto del bloque `else:` para que solo ejecute si las horas son válidas. El bloque completo queda:

```python
    if submitted:
        if not author.strip():
            st.error(t("ops_author_required"))
        elif not loop_url_input.strip():
            st.error(t("ops_loop_required_to_save"))
        elif effort_hours_input <= 0:
            st.error("Las horas invertidas son obligatorias y deben ser mayores a 0.")
        else:
            entry_group_id = uuid.uuid4().hex
            # ... resto igual que antes ...
```

- [ ] **Step 4: Pasar `effort_hours` solo a la nota `general`**

Dentro del loop `for ntype, ntext in (("general", general), ...)`, modificar el dict que se agrega a `notes_to_insert` para incluir `effort_hours` solo cuando `ntype == "general"`:

```python
            for ntype, ntext in (
                ("general", general),
                ("proximo_paso", proximo_paso),
                ("bloqueador", bloqueador),
                ("riesgo", riesgo),
            ):
                if str(ntext).strip():
                    notes_to_insert.append(
                        {
                            "project_id": selected_project.project_id,
                            "note_type": ntype,
                            "note_text": str(ntext).strip(),
                            "author": author.strip(),
                            "tags": "",
                            "is_private": False,
                            "entry_group_id": entry_group_id,
                            "note_title": "",
                            "progress_percent": progress_percent_value,
                            "estimated_end_date": estimated_end_date_value,
                            "effort_hours": effort_hours_input if ntype == "general" else None,
                        }
                    )
```

- [ ] **Step 5: Actualizar `insert_notes_batch` para aceptar y guardar `effort_hours`**

En `ui/tabs/seguimiento_operativo.py`, en la función `insert_notes_batch`, la línea que construye la tupla `cleaned.append(...)` debe incluir `effort_hours`, y la query INSERT también:

Cambiar la validación (línea ~445):
```python
        if note_type not in NOTE_TYPES and note_type != POST_CLOSURE_TYPE:
            continue
        if not note_text or not author:
            continue
```

Cambiar la tupla en `cleaned.append(...)`:
```python
        cleaned.append(
            (
                str(note.get("project_id", "")).strip(),
                note_text,
                note_type,
                author,
                str(note.get("tags", "")).strip(),
                1 if bool(note.get("is_private", False)) else 0,
                str(note.get("entry_group_id", "")).strip(),
                str(note.get("note_title", "")).strip(),
                progress_percent,
                str(note.get("estimated_end_date", "")).strip() or None,
                note.get("effort_hours"),   # nuevo
            )
        )
```

Cambiar la query `conn.executemany(...)`:
```python
    conn.executemany(
        """
        INSERT INTO project_notes
            (project_id, note_text, note_type, author, tags, is_private, entry_group_id, note_title,
             progress_percent, estimated_end_date, effort_hours)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        cleaned,
    )
```

- [ ] **Step 6: Verificar manualmente en Streamlit**

```bash
.venv\Scripts\python -m streamlit run start.py
```

1. Ir a Seguimiento Operativo → Captura rápida.
2. Seleccionar un proyecto activo.
3. Intentar guardar con horas = 0 → debe aparecer el error.
4. Llenar horas = 4.5 y texto en al menos un campo → debe guardar correctamente.
5. Verificar en BD:
```bash
.venv\Scripts\python -c "
import sqlite3
conn = sqlite3.connect('project_viability.db')
conn.row_factory = sqlite3.Row
rows = conn.execute('SELECT note_id, note_type, effort_hours FROM project_notes ORDER BY note_id DESC LIMIT 8').fetchall()
for r in rows: print(dict(r))
conn.close()
"
```
La nota `general` del último grupo debe tener `effort_hours = 4.5`, las demás `NULL`.

- [ ] **Step 7: Commit**

```bash
git add ui/tabs/seguimiento_operativo.py
git commit -m "feat: add mandatory effort_hours field to weekly note capture form"
```

---

## Task 5: Sección post-cierre para proyectos `implemented`

**Files:**
- Modify: `ui/tabs/seguimiento_operativo.py`

- [ ] **Step 1: Agregar sección post-cierre después del separador `st.markdown("---")`**

Después de la línea `st.markdown("---")` y antes de `_render_last_notes_cards(...)` (línea ~1199), agregar:

```python
    if str(selected_project.status or "").lower() == "implemented":
        st.subheader("Registrar actividad post-cierre")
        with st.form(key=f"ops_post_closure_form_{selected_project.project_id}", clear_on_submit=True):
            pc_author = st.text_input(
                t("ops_author"),
                value=default_author,
                key=f"ops_pc_author_{selected_project.project_id}",
            )
            pc_text = st.text_area(
                "Descripción de la actividad",
                placeholder="¿Qué se hizo? ¿Quién lo solicitó?",
                height=120,
                key=f"ops_pc_text_{selected_project.project_id}",
            )
            pc_hours = st.number_input(
                "Horas invertidas",
                min_value=0.0,
                max_value=80.0,
                value=0.0,
                step=0.5,
                key=f"ops_pc_hours_{selected_project.project_id}",
            )
            pc_submitted = st.form_submit_button("Guardar actividad post-cierre", type="primary")

        if pc_submitted:
            if not pc_author.strip():
                st.error(t("ops_author_required"))
            elif not str(pc_text).strip():
                st.error("La descripción de la actividad es obligatoria.")
            elif pc_hours <= 0:
                st.error("Las horas son obligatorias y deben ser mayores a 0.")
            else:
                try:
                    insert_notes_batch(conn, [{
                        "project_id": selected_project.project_id,
                        "note_type": POST_CLOSURE_TYPE,
                        "note_text": str(pc_text).strip(),
                        "author": pc_author.strip(),
                        "tags": "",
                        "is_private": False,
                        "entry_group_id": uuid.uuid4().hex,
                        "note_title": "Post-cierre",
                        "progress_percent": None,
                        "estimated_end_date": None,
                        "effort_hours": pc_hours,
                    }])
                    st.success("Actividad post-cierre registrada correctamente.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Error al guardar: {exc}")
```

- [ ] **Step 2: Verificar en Streamlit**

```bash
.venv\Scripts\python -m streamlit run start.py
```

1. Seleccionar un proyecto con status `implemented`.
2. Verificar que aparece la sección "Registrar actividad post-cierre".
3. Intentar guardar sin texto y sin horas → errores.
4. Guardar con texto + horas → éxito.
5. Verificar en BD:
```bash
.venv\Scripts\python -c "
import sqlite3
conn = sqlite3.connect('project_viability.db')
conn.row_factory = sqlite3.Row
rows = conn.execute(\"SELECT note_id, project_id, note_type, effort_hours FROM project_notes WHERE note_type='soporte_post_entrega'\").fetchall()
for r in rows: print(dict(r))
conn.close()
"
```

- [ ] **Step 3: Commit**

```bash
git add ui/tabs/seguimiento_operativo.py
git commit -m "feat: add post-closure activity section for implemented projects"
```

---

## Task 6: Bloque "Tiempo real" en el dashboard

**Files:**
- Modify: `ui/tabs/seguimiento_operativo.py` (función `_render_capture_tab` o donde se muestra la tarjeta del proyecto)

El bloque se agrega dentro de la función `_render_capture_tab`, después de `_render_last_notes_cards(...)`.

- [ ] **Step 1: Agregar función auxiliar de consulta de horas**

En `ui/tabs/seguimiento_operativo.py`, añadir esta función cerca de las demás funciones de consulta (después de `_latest_project_note`):

```python
def _get_project_hours(conn: sqlite3.Connection, project_id: str) -> dict[str, float]:
    """Retorna dev_hours y post_hours para un proyecto."""
    row = conn.execute(
        """
        SELECT
            COALESCE(SUM(CASE
                WHEN pn.note_type != 'soporte_post_entrega'
                 AND (p.closed_at IS NULL OR datetime(pn.created_at) <= datetime(p.closed_at))
                THEN pn.effort_hours ELSE 0
            END), 0) AS dev_hours,
            COALESCE(SUM(CASE
                WHEN pn.note_type = 'soporte_post_entrega'
                THEN pn.effort_hours ELSE 0
            END), 0) AS post_hours
        FROM projects p
        LEFT JOIN project_notes pn ON pn.project_id = p.project_id
        WHERE p.project_id = ? OR p.id = ?
        """,
        (project_id, project_id),
    ).fetchone()
    if row is None:
        return {"dev_hours": 0.0, "post_hours": 0.0}
    return {"dev_hours": float(row["dev_hours"]), "post_hours": float(row["post_hours"])}
```

- [ ] **Step 2: Renderizar el bloque en `_render_capture_tab`**

Al final de `_render_capture_tab`, después de `_render_last_notes_cards(...)`:

```python
    hours = _get_project_hours(conn, selected_project.project_id)
    dev_h = hours["dev_hours"]
    post_h = hours["post_hours"]
    total_h = dev_h + post_h

    if total_h > 0:
        st.markdown("---")
        st.markdown("**Tiempo real**")
        if post_h > 0:
            c1, c2, c3 = st.columns(3)
            c1.metric("Horas desarrollo", f"{dev_h:.1f} h")
            c2.metric("Horas post-cierre", f"{post_h:.1f} h")
            c3.metric("Total real", f"{total_h:.1f} h")
        else:
            c1, c2 = st.columns(2)
            c1.metric("Horas desarrollo", f"{dev_h:.1f} h")
            c2.metric("Total real", f"{total_h:.1f} h")
```

- [ ] **Step 3: Verificar en Streamlit**

```bash
.venv\Scripts\python -m streamlit run start.py
```

1. Seleccionar un proyecto que ya tenga notas con `effort_hours` registradas.
2. Verificar que el bloque "Tiempo real" aparece con los valores correctos.
3. Verificar que para proyectos sin ninguna hora registrada el bloque no aparece.
4. Verificar formato: `143.5 h`, no `143.500000 h`.

- [ ] **Step 4: Commit**

```bash
git add ui/tabs/seguimiento_operativo.py
git commit -m "feat: add Tiempo real metrics block to project capture tab"
```

---

## Task 7: Correr suite completa y cierre

- [ ] **Step 1: Correr todos los tests**

```bash
.venv\Scripts\python -m pytest tests/ -v --tb=short
```

Esperado: todos los tests existentes pasan + los nuevos de Task 1 y Task 3.

- [ ] **Step 2: Verificar backfill end-to-end**

```bash
.venv\Scripts\python scripts/export_notes_for_hours.py
```

Abre `notas_horas.csv` en Excel, llena algunas filas de `effort_hours` con valores > 0 (y deja alguna en blanco para probar el rechazo), luego:

```bash
.venv\Scripts\python scripts/import_notes_hours.py notas_horas.csv
```

Verificar que el output muestra actualizadas + rechazadas correctamente.

- [ ] **Step 3: Commit final de limpieza si hay cambios menores**

```bash
git add -p
git commit -m "chore: cleanup after effort-hours feature implementation"
```
