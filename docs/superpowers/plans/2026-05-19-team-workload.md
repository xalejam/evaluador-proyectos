# Team Workload Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Registrar múltiples miembros por proyecto en una tabla relacional y visualizar la carga del equipo (proyectos activos + horas acumuladas por persona) en el dashboard ejecutivo.

**Architecture:** Se agrega la tabla `project_members` a `project_viability.db` con migraciones idempotentes. Las funciones CRUD viven en `infra/db_migrations.py`. La UI expone una sección colapsable por proyecto para gestionar miembros, y una sección "Carga del equipo" al final del tab ejecutivo que muestra proyectos y horas por persona.

**Tech Stack:** Python 3.11+, SQLite3, Streamlit, pytest. Sin dependencias nuevas.

---

## Mapa de archivos

| Archivo | Acción | Responsabilidad |
|---|---|---|
| `infra/db_migrations.py` | Modificar | `ensure_members_schema`, CRUD (`get_project_members`, `add_project_member`, `remove_project_member`, `get_all_known_members`) |
| `ui/tabs/seguimiento_operativo.py` | Modificar | `_render_members_section`, `get_workload_df`, bloque "Carga del equipo" en `_render_executive_tab` |
| `tests/unit/test_team_workload.py` | Crear | Tests de migración, CRUD, y query de carga |

---

## Task 1: Schema y funciones CRUD de miembros

**Files:**
- Modify: `infra/db_migrations.py`
- Create: `tests/unit/test_team_workload.py`

- [ ] **Step 1: Crear el archivo de tests con los tests de migración y CRUD**

Crear `tests/unit/test_team_workload.py`:

```python
import sqlite3
import pytest
from infra.db_migrations import (
    ensure_projects_schema,
    ensure_members_schema,
    get_project_members,
    add_project_member,
    remove_project_member,
    get_all_known_members,
)


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    ensure_projects_schema(c)
    ensure_members_schema(c)
    yield c
    c.close()


def test_ensure_members_schema_creates_table(conn):
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    assert "project_members" in tables


def test_ensure_members_schema_is_idempotent(conn):
    ensure_members_schema(conn)
    ensure_members_schema(conn)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    assert "project_members" in tables


def test_add_member_persists(conn):
    add_project_member(conn, "P1", "Xiomara")
    members = get_project_members(conn, "P1")
    assert "Xiomara" in members


def test_duplicate_member_is_ignored(conn):
    add_project_member(conn, "P1", "Xiomara")
    add_project_member(conn, "P1", "Xiomara")  # no debe lanzar excepcion
    members = get_project_members(conn, "P1")
    assert members.count("Xiomara") == 1


def test_remove_member(conn):
    add_project_member(conn, "P1", "Xiomara")
    add_project_member(conn, "P1", "Ana")
    remove_project_member(conn, "P1", "Xiomara")
    members = get_project_members(conn, "P1")
    assert "Xiomara" not in members
    assert "Ana" in members


def test_get_project_members_returns_empty_list_for_unknown_project(conn):
    assert get_project_members(conn, "NOEXISTE") == []


def test_get_all_known_members_returns_unique_names(conn):
    add_project_member(conn, "P1", "Xiomara")
    add_project_member(conn, "P2", "Xiomara")
    add_project_member(conn, "P1", "Ana")
    names = get_all_known_members(conn)
    assert sorted(names) == ["Ana", "Xiomara"]
```

- [ ] **Step 2: Correr tests — deben fallar**

```bash
cd "c:\Users\ttMonroyX\OneDrive - Kantar\Documents\Project Managment\ReportesAdhoc\EvaluadorDeProyectos\Repositorio Evaluador"
.venv\Scripts\python -m pytest tests/unit/test_team_workload.py -v
```

Esperado: FAIL — `ensure_members_schema` no existe aún.

- [ ] **Step 3: Agregar `ensure_members_schema` y funciones CRUD en `infra/db_migrations.py`**

Al final del archivo, antes de `ensure_all_operational_schema`, agregar:

```python
def ensure_members_schema(conn: sqlite3.Connection) -> None:
    """Crea tabla project_members si no existe."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS project_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT NOT NULL,
            member_name TEXT NOT NULL,
            added_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(project_id, member_name)
        )
        """
    )
    _ensure_index(
        conn,
        "CREATE INDEX IF NOT EXISTS idx_project_members_pid ON project_members(project_id)",
    )
    conn.commit()


def get_project_members(conn: sqlite3.Connection, project_id: str) -> list[str]:
    """Retorna lista de nombres de miembros para un proyecto."""
    rows = conn.execute(
        "SELECT member_name FROM project_members WHERE project_id = ? ORDER BY added_at",
        (project_id,),
    ).fetchall()
    return [r[0] for r in rows]


def add_project_member(conn: sqlite3.Connection, project_id: str, member_name: str) -> None:
    """Agrega un miembro a un proyecto. Ignora duplicados silenciosamente."""
    conn.execute(
        "INSERT OR IGNORE INTO project_members (project_id, member_name) VALUES (?, ?)",
        (project_id.strip(), member_name.strip()),
    )
    conn.commit()


def remove_project_member(conn: sqlite3.Connection, project_id: str, member_name: str) -> None:
    """Elimina un miembro de un proyecto."""
    conn.execute(
        "DELETE FROM project_members WHERE project_id = ? AND member_name = ?",
        (project_id.strip(), member_name.strip()),
    )
    conn.commit()


def get_all_known_members(conn: sqlite3.Connection) -> list[str]:
    """Retorna todos los nombres de miembros únicos en toda la BD (para sugerencias)."""
    rows = conn.execute(
        "SELECT DISTINCT member_name FROM project_members ORDER BY member_name"
    ).fetchall()
    return [r[0] for r in rows]
```

También actualizar `ensure_all_operational_schema` para incluir la nueva migración:

```python
def ensure_all_operational_schema(conn: sqlite3.Connection) -> None:
    """Atajo para asegurar esquemas de projects/evaluations/notes."""
    ensure_projects_schema(conn)
    ensure_evaluations_schema(conn)
    ensure_notes_schema(conn)
    ensure_members_schema(conn)
```

- [ ] **Step 4: Correr tests — deben pasar**

```bash
.venv\Scripts\python -m pytest tests/unit/test_team_workload.py -v
```

Esperado: 7 PASSED.

- [ ] **Step 5: Aplicar migración a la BD real**

```bash
.venv\Scripts\python -c "
import sqlite3
from infra.db_migrations import ensure_members_schema
conn = sqlite3.connect('project_viability.db')
ensure_members_schema(conn)
conn.close()
print('OK')
"
```

Esperado: `OK` sin errores.

- [ ] **Step 6: Commit**

```bash
git add infra/db_migrations.py tests/unit/test_team_workload.py
git commit -m "feat: add project_members table with CRUD functions"
```

---

## Task 2: Query de carga del equipo y su test

**Files:**
- Modify: `tests/unit/test_team_workload.py`
- Modify: `ui/tabs/seguimiento_operativo.py`

- [ ] **Step 1: Agregar tests de `get_workload_df` al archivo de tests**

Añadir al final de `tests/unit/test_team_workload.py`:

```python
import pandas as pd
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from infra.db_migrations import ensure_notes_schema


@pytest.fixture
def conn_with_data():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    ensure_projects_schema(c)
    ensure_members_schema(c)
    ensure_notes_schema(c)
    # Proyectos
    c.execute("INSERT INTO projects (id, project_id, name, status) VALUES ('P1','P1','Proyecto Alpha','executing')")
    c.execute("INSERT INTO projects (id, project_id, name, status) VALUES ('P2','P2','Proyecto Beta','executing')")
    c.execute("INSERT INTO projects (id, project_id, name, status) VALUES ('P3','P3','Proyecto Gamma','approved')")
    # Miembros
    c.execute("INSERT INTO project_members (project_id, member_name) VALUES ('P1','Xiomara')")
    c.execute("INSERT INTO project_members (project_id, member_name) VALUES ('P2','Xiomara')")
    c.execute("INSERT INTO project_members (project_id, member_name) VALUES ('P1','Ana')")
    c.execute("INSERT INTO project_members (project_id, member_name) VALUES ('P3','Ana')")
    # Horas en notas
    c.execute("INSERT INTO project_notes (project_id, note_text, note_type, author, effort_hours) VALUES ('P1','x','general','Xiomara',10.0)")
    c.execute("INSERT INTO project_notes (project_id, note_text, note_type, author, effort_hours) VALUES ('P1','x','general','Xiomara',5.0)")
    c.execute("INSERT INTO project_notes (project_id, note_text, note_type, author, effort_hours) VALUES ('P2','x','general','Xiomara',20.0)")
    c.commit()
    yield c
    c.close()


def test_workload_df_sums_hours_per_project(conn_with_data):
    from ui.tabs.seguimiento_operativo import get_workload_df
    df = get_workload_df(conn_with_data, statuses=["executing", "approved"])
    p1_xiomara = df[(df["member_name"] == "Xiomara") & (df["project_id"] == "P1")]
    assert len(p1_xiomara) == 1
    assert p1_xiomara.iloc[0]["total_hours"] == 15.0


def test_workload_df_empty_when_no_members(conn_with_data):
    from ui.tabs.seguimiento_operativo import get_workload_df
    # Proyecto sin miembros
    conn_with_data.execute("INSERT INTO projects (id, project_id, name, status) VALUES ('P9','P9','Sin miembros','executing')")
    conn_with_data.commit()
    df = get_workload_df(conn_with_data, statuses=["executing"])
    # P9 no debe aparecer (no tiene miembros)
    assert "P9" not in df["project_id"].values


def test_workload_df_filters_by_status(conn_with_data):
    from ui.tabs.seguimiento_operativo import get_workload_df
    df = get_workload_df(conn_with_data, statuses=["executing"])
    # P3 es 'approved', no debe aparecer
    assert "P3" not in df["project_id"].values
```

- [ ] **Step 2: Correr tests nuevos — deben fallar**

```bash
.venv\Scripts\python -m pytest tests/unit/test_team_workload.py::test_workload_df_sums_hours_per_project -v
```

Esperado: FAIL — `get_workload_df` no existe aún.

- [ ] **Step 3: Agregar `get_workload_df` en `ui/tabs/seguimiento_operativo.py`**

Agregar después de la función `_get_project_hours` (alrededor de línea 613):

```python
def get_workload_df(conn: sqlite3.Connection, statuses: list[str]) -> pd.DataFrame:
    """Retorna DataFrame con carga por miembro: member_name, project_id, name, status, total_hours."""
    if not statuses:
        return pd.DataFrame(columns=["member_name", "project_id", "name", "status", "total_hours"])
    placeholders = ",".join(["?"] * len(statuses))
    rows = conn.execute(
        f"""
        SELECT
            pm.member_name,
            p.project_id,
            p.name,
            p.status,
            COALESCE(SUM(pn.effort_hours), 0) AS total_hours
        FROM project_members pm
        JOIN projects p ON p.project_id = pm.project_id
        LEFT JOIN project_notes pn ON pn.project_id = p.project_id
        WHERE p.status IN ({placeholders})
        GROUP BY pm.member_name, p.project_id, p.name, p.status
        ORDER BY pm.member_name, total_hours DESC
        """,
        statuses,
    ).fetchall()
    if not rows:
        return pd.DataFrame(columns=["member_name", "project_id", "name", "status", "total_hours"])
    return pd.DataFrame([dict(r) for r in rows])
```

- [ ] **Step 4: Correr todos los tests de team workload**

```bash
.venv\Scripts\python -m pytest tests/unit/test_team_workload.py -v
```

Esperado: 10 PASSED.

- [ ] **Step 5: Commit**

```bash
git add ui/tabs/seguimiento_operativo.py tests/unit/test_team_workload.py
git commit -m "feat: add get_workload_df query for team workload dashboard"
```

---

## Task 3: UI — Sección de gestión de miembros por proyecto

**Files:**
- Modify: `ui/tabs/seguimiento_operativo.py`

La sección se agrega dentro de `_render_capture_tab`, justo después del expander `project_links_section` (alrededor de línea 1070, después del bloque `with st.expander(t("project_links_section"), ...)`).

- [ ] **Step 1: Agregar el import de funciones CRUD en `ui/tabs/seguimiento_operativo.py`**

Al inicio del archivo, en el bloque de imports de `infra.db_migrations`, agregar las funciones nuevas. Buscar la línea:

```python
from infra.db_migrations import update_project_status  # noqa: E402
```

Reemplazar con:

```python
from infra.db_migrations import (  # noqa: E402
    update_project_status,
    get_project_members,
    add_project_member,
    remove_project_member,
    get_all_known_members,
    ensure_members_schema,
)
```

- [ ] **Step 2: Agregar función `_render_members_section` en `ui/tabs/seguimiento_operativo.py`**

Agregar después de la función `get_workload_df`:

```python
def _render_members_section(conn: sqlite3.Connection, project_id: str) -> None:
    """Sección colapsable para gestionar miembros del equipo de un proyecto."""
    with st.expander("Equipo del proyecto", expanded=False):
        members = get_project_members(conn, project_id)
        all_known = get_all_known_members(conn)

        if members:
            st.markdown("**Miembros actuales:**")
            for member in members:
                col_name, col_btn = st.columns([4, 1])
                col_name.write(member)
                confirm_key = f"ops_confirm_remove_{project_id}_{member}"
                if col_btn.button("✕", key=f"ops_remove_{project_id}_{member}", help=f"Eliminar {member}"):
                    st.session_state[confirm_key] = True
                if st.session_state.get(confirm_key):
                    st.warning(f"¿Eliminar a **{member}** de este proyecto?")
                    c1, c2 = st.columns(2)
                    if c1.button("Confirmar", key=f"ops_confirm_yes_{project_id}_{member}", type="primary"):
                        remove_project_member(conn, project_id, member)
                        st.session_state.pop(confirm_key, None)
                        st.rerun()
                    if c2.button("Cancelar", key=f"ops_confirm_no_{project_id}_{member}"):
                        st.session_state.pop(confirm_key, None)
                        st.rerun()
        else:
            st.caption("Sin miembros asignados aún.")

        st.markdown("**Agregar miembro:**")
        suggestions = ["Nuevo..."] + [n for n in all_known if n not in members]
        selected = st.selectbox(
            "Seleccionar o escribir",
            options=suggestions,
            key=f"ops_member_select_{project_id}",
            label_visibility="collapsed",
        )
        new_name_input = ""
        if selected == "Nuevo...":
            new_name_input = st.text_input(
                "Nombre del nuevo miembro",
                key=f"ops_member_new_{project_id}",
                placeholder="Ej. Carlos",
            )
        name_to_add = new_name_input.strip() if selected == "Nuevo..." else selected

        if st.button("+ Agregar", key=f"ops_member_add_{project_id}"):
            if not name_to_add:
                st.error("El nombre no puede estar vacío.")
            elif name_to_add in members:
                st.warning(f"{name_to_add} ya es miembro de este proyecto.")
            else:
                add_project_member(conn, project_id, name_to_add)
                st.success(f"{name_to_add} agregado al equipo.")
                st.rerun()
```

- [ ] **Step 3: Llamar a `_render_members_section` en `_render_capture_tab`**

Buscar en `_render_capture_tab` la línea que abre el expander de links:

```python
    with st.expander(t("project_links_section"), expanded=bool(st.session_state.get(links_expand_key, False))):
```

Justo después del cierre de ese bloque `with st.expander(...)` (después del `st.button(t("save_links"), ...)` y su bloque), agregar:

```python
    _render_members_section(conn, selected_project.project_id)
```

Para encontrar el lugar exacto, busca la línea:

```python
    default_author = str(st.session_state.get("author", st.session_state.get("current_user", "Xiomara Monroy")))
```

Y agregar la llamada justo antes de esa línea:

```python
    _render_members_section(conn, selected_project.project_id)

    default_author = str(st.session_state.get("author", st.session_state.get("current_user", "Xiomara Monroy")))
```

- [ ] **Step 4: Asegurar que `ensure_members_schema` se llama al arrancar la conexión**

Buscar en el archivo donde se llama `ensure_schema` o las migraciones al iniciar. Buscar la función `get_conn` o el bloque de inicialización del tab. Localizar con:

```bash
.venv\Scripts\python -c "
import ast, sys
src = open('ui/tabs/seguimiento_operativo.py').read()
for i, line in enumerate(src.splitlines(), 1):
    if 'ensure_schema' in line or 'ensure_all' in line:
        print(i, line)
"
```

En esa línea de inicialización, agregar `ensure_members_schema(conn)` si no se llama ya vía `ensure_all_operational_schema`. Si `ensure_all_operational_schema` ya está siendo llamado (lo actualizamos en Task 1), no se necesita nada adicional.

- [ ] **Step 5: Verificar que el módulo importa sin errores**

```bash
.venv\Scripts\python -c "import ui.tabs.seguimiento_operativo; print('OK')"
```

Esperado: `OK`

- [ ] **Step 6: Commit**

```bash
git add ui/tabs/seguimiento_operativo.py
git commit -m "feat: add team members management section to project capture tab"
```

---

## Task 4: UI — Bloque "Carga del equipo" en el dashboard ejecutivo

**Files:**
- Modify: `ui/tabs/seguimiento_operativo.py`

El bloque se agrega al final de `_render_executive_tab`, después del gráfico de línea de avance por proyecto (después de `st.line_chart(...)`).

- [ ] **Step 1: Agregar la función `_render_workload_section` en `ui/tabs/seguimiento_operativo.py`**

Agregar justo antes de la función `_render_executive_tab`:

```python
def _render_workload_section(conn: sqlite3.Connection, statuses: list[str]) -> None:
    """Renderiza el bloque Carga del equipo al final del tab ejecutivo."""
    st.markdown("---")
    st.subheader("Carga del equipo")

    df = get_workload_df(conn, statuses=statuses)

    if df.empty:
        st.info("Aún no hay miembros asignados a proyectos.")
        return

    for member_name, group in df.groupby("member_name"):
        active_count = len(group)
        total_hours = group["total_hours"].sum()

        st.markdown(f"#### {member_name}")
        c1, c2 = st.columns(2)
        c1.metric("Proyectos activos", active_count)
        c2.metric("Horas acumuladas", f"{total_hours:.1f} h")

        display = group[["name", "status", "total_hours"]].copy()
        display.columns = ["Proyecto", "Status", "Horas"]
        display["Horas"] = display["Horas"].apply(lambda h: f"{h:.1f} h")
        display["Status"] = display["Status"].apply(label_status)
        st.dataframe(display, use_container_width=True, hide_index=True)
        st.divider()
```

- [ ] **Step 2: Llamar a `_render_workload_section` al final de `_render_executive_tab`**

Buscar el final de `_render_executive_tab`. La última línea del gráfico de progreso es:

```python
        st.line_chart(
            progress_compare_df,
            x_label="Registro",
            y_label=t("ops_progress_percent_label"),
            use_container_width=True,
        )
```

Después del bloque `if not series_by_project: ... else: ...` que contiene ese `st.line_chart`, agregar:

```python
    _render_workload_section(conn, statuses=status_filter if status_filter else list(ONGOING_STATUSES))
```

- [ ] **Step 3: Verificar que el módulo importa sin errores**

```bash
.venv\Scripts\python -c "import ui.tabs.seguimiento_operativo; print('OK')"
```

Esperado: `OK`

- [ ] **Step 4: Commit**

```bash
git add ui/tabs/seguimiento_operativo.py
git commit -m "feat: add Carga del equipo workload section to executive dashboard"
```

---

## Task 5: Suite completa de tests y cierre

- [ ] **Step 1: Correr todos los tests**

```bash
.venv\Scripts\python -m pytest tests/ -v --tb=short
```

Esperado: todos los tests existentes pasan + los 10 nuevos de team workload.

- [ ] **Step 2: Verificar backfill de miembros en BD real (opcional)**

Si ya hay proyectos activos en la BD y quieres asignar miembros desde consola:

```bash
.venv\Scripts\python -c "
import sqlite3
from infra.db_migrations import add_project_member, get_project_members
conn = sqlite3.connect('project_viability.db')

# Reemplazar 'MX-XIOMY-0001' con el project_id real
add_project_member(conn, 'MX-XIOMY-0001', 'Xiomara')
print(get_project_members(conn, 'MX-XIOMY-0001'))
conn.close()
"
```

- [ ] **Step 3: Commit final si hay cambios menores de limpieza**

```bash
git add -p
git commit -m "chore: cleanup after team workload feature implementation"
```
