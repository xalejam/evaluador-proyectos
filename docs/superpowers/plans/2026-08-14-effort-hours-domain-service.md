# Effort Hours Domain Service Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminar la inconsistencia entre el INSERT propio de `ui/tabs/seguimiento_operativo.py` (que sí persiste `effort_hours`) y la ruta de dominio `OperationalTrackingService.add_update` → `NotesRepository.insert_notes_batch` (que la descarta silenciosamente), para que exista una única fuente de verdad al escribir `project_notes`.

**Architecture:** `NotesRepository.insert_notes_batch` gana un campo opcional `effort_hours` en cada dict de nota y lo agrega a la lista de columnas del INSERT. `OperationalTrackingService.add_update` gana un parámetro `effort_hours: float | None = None` que solo se adjunta a la nota de tipo `general` (mismo criterio que ya usa hoy el helper local de la UI). El formulario de captura semanal en `ui/tabs/seguimiento_operativo.py` deja de llamar a su función `insert_notes_batch` local y en su lugar instancia `OperationalTrackingService` y llama a `add_update(...)`. La sección de actividad post-cierre (`soporte_post_entrega`) no pasa por `add_update` porque ese tipo de nota no es uno de los cuatro que el servicio soporta — queda fuera de alcance de este plan y se documenta como decisión consciente en el Task 3.

**Tech Stack:** Python 3.11+, SQLite3, Streamlit, pytest. Sin dependencias nuevas.

**Spec:** N/A — requisito directo del usuario (no hay spec/design doc previo para este cambio puntual).

## Global Constraints

- No modificar el esquema de `project_notes`: la columna `effort_hours` ya existe (agregada por `docs/superpowers/plans/2026-05-19-effort-hours-tracking.md`).
- No tocar la función local `insert_notes_batch` de `ui/tabs/seguimiento_operativo.py` ni el flujo de "Registrar actividad post-cierre": siguen usándola porque escriben `note_type = "soporte_post_entrega"`, que `OperationalTrackingService.add_update` no soporta.
- `effort_hours` se adjunta únicamente a la nota `general` del grupo, igual que hace hoy el helper local de la UI.

---

## Mapa de archivos

| Archivo | Acción | Responsabilidad |
|---|---|---|
| `infra/db/repositories/notes_repo.py` | Modificar | `NotesRepository.insert_notes_batch` acepta y persiste `effort_hours` |
| `tests/integration/test_repositories.py` | Modificar | Tests de persistencia de `effort_hours` en `NotesRepository` |
| `domain/services/seguimiento_operativo_service.py` | Modificar | `OperationalTrackingService.add_update` acepta `effort_hours` y lo adjunta solo a la nota `general` |
| `tests/unit/test_effort_hours_domain_service.py` | Crear | Tests de round-trip de `effort_hours` a través del servicio de dominio |
| `ui/tabs/seguimiento_operativo.py` | Modificar | El formulario de captura semanal llama a `OperationalTrackingService.add_update` en vez de a su `insert_notes_batch` local |

---

## Task 1: `NotesRepository.insert_notes_batch` persiste `effort_hours`

**Files:**
- Modify: `infra/db/repositories/notes_repo.py`
- Test: `tests/integration/test_repositories.py`

**Interfaces:**
- Produces: `NotesRepository.insert_notes_batch(notes: list[dict[str, Any]]) -> list[int]` — cada dict de `notes` acepta ahora una clave opcional `"effort_hours"` (`float | None`, default `None` si falta o es `""`), persistida en `project_notes.effort_hours`.

- [ ] **Step 1: Escribir los tests que fallan**

Agregar a `tests/integration/test_repositories.py` (agregar `import sqlite3` al inicio del archivo si no está):

```python
import sqlite3

from infra.db.repositories.evaluation_repo import EvaluationRepository
from infra.db.repositories.notes_repo import NotesRepository
from infra.db.repositories.project_repo import ProjectRepository
```

Y al final del archivo:

```python
def test_notes_repo_insert_persists_effort_hours(temp_db_path):
    project_repo = ProjectRepository(str(temp_db_path))
    notes_repo = NotesRepository(str(temp_db_path))
    _seed_project(project_repo)

    note_ids = notes_repo.insert_notes_batch(
        [
            {
                "project_id": "MX-TEST-0001",
                "note_type": "general",
                "note_text": "Avance semanal",
                "author": "tester",
                "entry_group_id": "grp-hours",
                "effort_hours": 6.5,
            }
        ]
    )

    conn = sqlite3.connect(str(temp_db_path))
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT effort_hours FROM project_notes WHERE note_id = ?", (note_ids[0],)).fetchone()
    conn.close()
    assert row["effort_hours"] == 6.5


def test_notes_repo_insert_effort_hours_defaults_to_none(temp_db_path):
    project_repo = ProjectRepository(str(temp_db_path))
    notes_repo = NotesRepository(str(temp_db_path))
    _seed_project(project_repo)

    note_ids = notes_repo.insert_notes_batch(
        [
            {
                "project_id": "MX-TEST-0001",
                "note_type": "general",
                "note_text": "Sin horas",
                "author": "tester",
                "entry_group_id": "grp-no-hours",
            }
        ]
    )

    conn = sqlite3.connect(str(temp_db_path))
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT effort_hours FROM project_notes WHERE note_id = ?", (note_ids[0],)).fetchone()
    conn.close()
    assert row["effort_hours"] is None
```

- [ ] **Step 2: Correr los tests nuevos — deben fallar**

```bash
.venv\Scripts\python -m pytest tests/integration/test_repositories.py::test_notes_repo_insert_persists_effort_hours tests/integration/test_repositories.py::test_notes_repo_insert_effort_hours_defaults_to_none -v
```

Esperado: FAIL — `test_notes_repo_insert_persists_effort_hours` falla porque `effort_hours` queda `None` aunque se pasó `6.5` (la columna no está en el INSERT).

- [ ] **Step 3: Modificar `infra/db/repositories/notes_repo.py`**

Reemplazar el cuerpo de `insert_notes_batch`:

```python
    def insert_notes_batch(self, notes: list[dict[str, Any]]) -> list[int]:
        from infra.db.adapter import db_now

        now = db_now()
        cleaned = []
        for n in notes:
            if not str(n.get("project_id", "")).strip() or not str(n.get("note_text", "")).strip():
                continue
            progress_percent = n.get("progress_percent")
            if progress_percent in ("", None):
                progress_percent = None
            elif not isinstance(progress_percent, int):
                raise ValueError("progress_percent must be an integer between 0 and 100.")
            if progress_percent is not None and not (0 <= progress_percent <= 100):
                raise ValueError("progress_percent must be between 0 and 100.")
            effort_hours = n.get("effort_hours")
            if effort_hours in ("", None):
                effort_hours = None
            cleaned.append(
                (
                    str(n.get("project_id", "")).strip(),
                    str(n.get("note_text", "")).strip(),
                    str(n.get("note_type", "general")).strip(),
                    str(n.get("author", "")).strip(),
                    str(n.get("tags", "")).strip(),
                    1 if bool(n.get("is_private", False)) else 0,
                    str(n.get("entry_group_id", "")).strip(),
                    str(n.get("note_title", "")).strip(),
                    progress_percent,
                    str(n.get("estimated_end_date", "")).strip() or None,
                    effort_hours,
                    now,
                )
            )
        if not cleaned:
            return []

        placeholders_str = ", ".join([PLACEHOLDER] * 12)
        with get_sqlite_conn(self.db_path) as conn:
            conn.executemany(
                f"""
                INSERT INTO project_notes
                    (
                        project_id, note_text, note_type, author, tags, is_private, entry_group_id, note_title,
                        progress_percent, estimated_end_date, effort_hours, created_at
                    )
                VALUES ({placeholders_str})
                """,
                cleaned,
            )
            if IS_CLOUD:
                row = conn.execute("SELECT MAX(note_id) AS last_id FROM project_notes").fetchone()
            else:
                row = conn.execute("SELECT last_insert_rowid() AS last_id").fetchone()
            conn.commit()
            last_id = int(row["last_id"]) if row else 0
            first_id = max(1, last_id - len(cleaned) + 1)
            return list(range(first_id, last_id + 1))
```

- [ ] **Step 4: Correr los tests — deben pasar**

```bash
.venv\Scripts\python -m pytest tests/integration/test_repositories.py -v
```

Esperado: todos PASSED, incluyendo los 2 nuevos.

- [ ] **Step 5: Commit**

```bash
git add infra/db/repositories/notes_repo.py tests/integration/test_repositories.py
git commit -m "feat: persistir effort_hours en NotesRepository.insert_notes_batch"
```

---

## Task 2: `OperationalTrackingService.add_update` acepta `effort_hours`

**Files:**
- Modify: `domain/services/seguimiento_operativo_service.py`
- Create: `tests/unit/test_effort_hours_domain_service.py`

**Interfaces:**
- Consumes: `NotesRepository.insert_notes_batch` del Task 1 — clave opcional `"effort_hours"` en cada dict de nota.
- Produces: `OperationalTrackingService.add_update(project_id: str, payload_4_textareas: dict[str, str], author: str, tags: str, note_title: str = "", progress_percent: int | None = None, estimated_end_date: str | None = None, effort_hours: float | None = None) -> list[int]`. `effort_hours` se adjunta únicamente a la nota de tipo `"general"`; las demás notas del mismo grupo (`proximo_paso`, `bloqueador`, `riesgo`) reciben `effort_hours = None`.

- [ ] **Step 1: Escribir los tests que fallan**

Crear `tests/unit/test_effort_hours_domain_service.py`:

```python
import sqlite3
import tempfile

from domain.services.seguimiento_operativo_service import OperationalTrackingService


def _service() -> OperationalTrackingService:
    tmp = tempfile.mktemp(suffix=".db")
    svc = OperationalTrackingService(tmp)
    svc.ensure_schema()
    return svc


def _last_effort_hours(db_path: str, note_type: str):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT effort_hours FROM project_notes WHERE note_type = ? ORDER BY note_id DESC LIMIT 1",
        (note_type,),
    ).fetchone()
    conn.close()
    return row["effort_hours"] if row else None


def test_add_update_persists_effort_hours_on_general_note():
    svc = _service()
    svc.add_update(
        "P1",
        {"general": "Avance semanal", "proximo_paso": "", "bloqueador": "", "riesgo": ""},
        "Xiomara",
        "",
        effort_hours=6.5,
    )
    assert _last_effort_hours(svc.db_path, "general") == 6.5


def test_add_update_does_not_attach_effort_hours_to_other_note_types():
    svc = _service()
    svc.add_update(
        "P1",
        {"general": "Avance", "proximo_paso": "Siguiente paso", "bloqueador": "", "riesgo": ""},
        "Xiomara",
        "",
        effort_hours=3.0,
    )
    assert _last_effort_hours(svc.db_path, "proximo_paso") is None


def test_add_update_effort_hours_defaults_to_none():
    svc = _service()
    svc.add_update(
        "P1",
        {"general": "Avance sin horas", "proximo_paso": "", "bloqueador": "", "riesgo": ""},
        "Xiomara",
        "",
    )
    assert _last_effort_hours(svc.db_path, "general") is None
```

- [ ] **Step 2: Correr los tests — deben fallar**

```bash
.venv\Scripts\python -m pytest tests/unit/test_effort_hours_domain_service.py -v
```

Esperado: FAIL con `TypeError: add_update() got an unexpected keyword argument 'effort_hours'`.

- [ ] **Step 3: Modificar `add_update` en `domain/services/seguimiento_operativo_service.py`**

```python
    def add_update(
        self,
        project_id: str,
        payload_4_textareas: dict[str, str],
        author: str,
        tags: str,
        note_title: str = "",
        progress_percent: int | None = None,
        estimated_end_date: str | None = None,
        effort_hours: float | None = None,
    ) -> list[int]:
        entry_group_id = uuid.uuid4().hex
        notes = []
        for ntype in ("general", "proximo_paso", "bloqueador", "riesgo"):
            txt = str(payload_4_textareas.get(ntype, "")).strip()
            if txt:
                notes.append(
                    {
                        "project_id": project_id,
                        "note_type": ntype,
                        "note_text": txt,
                        "author": author,
                        "tags": tags,
                        "entry_group_id": entry_group_id,
                        "note_title": note_title,
                        "is_private": False,
                        "progress_percent": progress_percent,
                        "estimated_end_date": estimated_end_date,
                        "effort_hours": effort_hours if ntype == "general" else None,
                    }
                )
        return self.notes_repo.insert_notes_batch(notes)
```

- [ ] **Step 4: Correr los tests — deben pasar**

```bash
.venv\Scripts\python -m pytest tests/unit/test_effort_hours_domain_service.py -v
```

Esperado: 3 PASSED.

- [ ] **Step 5: Correr toda la suite para detectar regresiones**

```bash
.venv\Scripts\python -m pytest tests/ -v --tb=short
```

Esperado: todos los tests existentes siguen pasando.

- [ ] **Step 6: Commit**

```bash
git add domain/services/seguimiento_operativo_service.py tests/unit/test_effort_hours_domain_service.py
git commit -m "feat: propagar effort_hours a traves de OperationalTrackingService.add_update"
```

---

## Task 3: El formulario de captura semanal usa el servicio de dominio

**Files:**
- Modify: `ui/tabs/seguimiento_operativo.py`

**Interfaces:**
- Consumes: `OperationalTrackingService.add_update(...)` del Task 2.

- [ ] **Step 1: Importar `OperationalTrackingService`**

En el bloque de imports de `ui/tabs/seguimiento_operativo.py` (justo antes de `from infra.db.adapter import PLACEHOLDER, db_read_dataframe`), agregar:

```python
from domain.services.seguimiento_operativo_service import OperationalTrackingService
from infra.db.adapter import PLACEHOLDER, db_read_dataframe
```

- [ ] **Step 2: Reemplazar el bloque `if submitted:` del formulario de captura semanal**

Ubicar en `_render_capture_tab` el bloque que arranca en `if submitted:` (después del `with st.form(key=f"ops_capture_form_{selected_project.project_id}", ...)`). Reemplazar todo el bloque:

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
            progress_percent_value = int(progress_percent_input) if enable_progress_capture else None
            estimated_end_date_value = (
                estimated_end_date_input.isoformat() if isinstance(estimated_end_date_input, date) else None
            )
            notes_to_insert = []
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

            if not notes_to_insert:
                st.warning(t("ops_no_content_to_save"))
            else:
                try:
                    if loop_url_input.strip() != (selected_project.loop_url or "").strip():
                        upsert_project_loop_url(conn, selected_project.project_id, loop_url_input)
                    inserted_ids = insert_notes_batch(conn, notes_to_insert)
                    status_after: str | None = None
                    if str(selected_project.status or "").lower() in START_EXECUTION_STATUSES:
                        status_after = "executing"
                    if status_after:
                        update_project_status(conn, selected_project.project_id, status_after)
                    st.success(
                        f"{t('ops_update_saved')} {entry_group_id}. {t('ops_notes_inserted')}: {len(inserted_ids)}"
                    )
                    if status_after:
                        st.info(f"{t('ops_status_changed_to')} {label_status(status_after)}")
                    st.session_state[capture_saved_key] = True
                    st.rerun()
                except Exception as exc:
                    st.error(f"{t('ops_save_update_error')}: {exc}")
```

por:

```python
    if submitted:
        if not author.strip():
            st.error(t("ops_author_required"))
        elif not loop_url_input.strip():
            st.error(t("ops_loop_required_to_save"))
        elif effort_hours_input <= 0:
            st.error("Las horas invertidas son obligatorias y deben ser mayores a 0.")
        else:
            progress_percent_value = int(progress_percent_input) if enable_progress_capture else None
            estimated_end_date_value = (
                estimated_end_date_input.isoformat() if isinstance(estimated_end_date_input, date) else None
            )
            payload_4_textareas = {
                "general": str(general).strip(),
                "proximo_paso": str(proximo_paso).strip(),
                "bloqueador": str(bloqueador).strip(),
                "riesgo": str(riesgo).strip(),
            }

            if not any(payload_4_textareas.values()):
                st.warning(t("ops_no_content_to_save"))
            else:
                try:
                    if loop_url_input.strip() != (selected_project.loop_url or "").strip():
                        upsert_project_loop_url(conn, selected_project.project_id, loop_url_input)
                    tracking_service = OperationalTrackingService(DB_PATH)
                    tracking_service.ensure_schema()
                    inserted_ids = tracking_service.add_update(
                        selected_project.project_id,
                        payload_4_textareas,
                        author.strip(),
                        "",
                        note_title="",
                        progress_percent=progress_percent_value,
                        estimated_end_date=estimated_end_date_value,
                        effort_hours=effort_hours_input,
                    )
                    status_after: str | None = None
                    if str(selected_project.status or "").lower() in START_EXECUTION_STATUSES:
                        status_after = "executing"
                    if status_after:
                        update_project_status(conn, selected_project.project_id, status_after)
                    st.success(f"{t('ops_notes_inserted')}: {len(inserted_ids)}")
                    if status_after:
                        st.info(f"{t('ops_status_changed_to')} {label_status(status_after)}")
                    st.session_state[capture_saved_key] = True
                    st.rerun()
                except Exception as exc:
                    st.error(f"{t('ops_save_update_error')}: {exc}")
```

Nota: `tracking_service.ensure_schema()` es idempotente (usa `ensure_projects_schema`/`ensure_notes_schema`, que a su vez llaman `_add_column_if_missing`) y garantiza que la columna `effort_hours` exista aunque la tabla se haya creado solo con el `ensure_schema` local de este archivo, que no la agrega. El mensaje de éxito deja de mostrar `entry_group_id` (dato interno de correlación, no accionable para el usuario) porque `add_update` no lo retorna; conserva el conteo de notas insertadas.

- [ ] **Step 3: Verificar que el módulo importa sin errores**

```bash
.venv\Scripts\python -c "import ui.tabs.seguimiento_operativo; print('OK')"
```

Esperado: `OK`

- [ ] **Step 4: Correr toda la suite de tests**

```bash
.venv\Scripts\python -m pytest tests/ -v --tb=short
```

Esperado: todos los tests pasan (incluidos los de Task 1 y Task 2).

- [ ] **Step 5: Verificar manualmente en Streamlit**

```bash
.venv\Scripts\python -m streamlit run start.py
```

1. Ir a Seguimiento Operativo → Captura rápida.
2. Seleccionar un proyecto activo, llenar horas = 4.5 y texto en "General".
3. Guardar y confirmar el mensaje de éxito con el conteo de notas.
4. Verificar en BD que la nota `general` quedó con `effort_hours = 4.5`:

```bash
.venv\Scripts\python -c "
import sqlite3
conn = sqlite3.connect('project_viability.db')
conn.row_factory = sqlite3.Row
rows = conn.execute('SELECT note_id, note_type, effort_hours FROM project_notes ORDER BY note_id DESC LIMIT 5').fetchall()
for r in rows: print(dict(r))
conn.close()
"
```

- [ ] **Step 6: Commit**

```bash
git add ui/tabs/seguimiento_operativo.py
git commit -m "refactor: el formulario de captura semanal usa OperationalTrackingService.add_update"
```
