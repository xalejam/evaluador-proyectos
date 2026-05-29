"""Seguimiento Operativo v2 (notas inmutables por proyecto).

Este modulo usa SQLite en `project_viability.db` y puede ejecutarse de forma
independiente con:

    streamlit run seguimiento_operativo.py
"""

from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass
from datetime import date
from typing import Any

import pandas as pd
import streamlit as st

from infra.db.adapter import PLACEHOLDER, db_read_dataframe
from infra.db.connection import get_sqlite_conn as get_conn
from infra.presentation_ports import (
    InMemoryDestination,
    SqliteDataSource,
)
from infra.presentation_ports import (
    build_presentation_bytes as _build_pptx_bytes,
)
from infra.status_machine import can_transition
from ui.i18n_labels import label_note_type, label_status
from ui.tabs.shared import t

# Configuracion (editable)
DB_PATH = "project_viability.db"
ONGOING_STATUSES = (
    "evaluated",
    "approved",
    "in_agenda",
    "backlog",
    "on_hold",
    "rejected",
    "executing",
    "implemented",
    "handed_off",
)
CAPTURE_DEFAULT_STATUSES = ("approved", "in_agenda", "executing")
NOTE_TYPES = ("general", "proximo_paso", "bloqueador", "riesgo")
ARTIFACT_TYPES = ("azure_devops", "sharepoint", "powerbi", "excel_vba", "folder", "agent", "other")
TECH_STACK_OPTIONS = ("python", "vba", "powerbi", "agent", "other")
START_EXECUTION_STATUSES = ("evaluated", "approved", "in_agenda")
POST_CLOSURE_TYPE = "soporte_post_entrega"


def _note_type_help() -> dict[str, str]:
    return {
        "general": t("ops_note_help_general"),
        "proximo_paso": t("ops_note_help_next_step"),
        "bloqueador": t("ops_note_help_blocker"),
        "riesgo": t("ops_note_help_risk"),
    }


def _note_type_example() -> dict[str, str]:
    return {
        "general": t("ops_note_example_general"),
        "proximo_paso": t("ops_note_example_next_step"),
        "bloqueador": t("ops_note_example_blocker"),
        "riesgo": t("ops_note_example_risk"),
    }


@dataclass(frozen=True)
class Project:
    project_id: str
    name: str
    status: str
    owner: str
    country: str
    created_at: str
    updated_at: str
    loop_url: str
    repo_url: str
    artifacts_url: str
    artifacts_type: str
    tech_stack: str


def _connect(path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def _table_exists(conn, table_name: str) -> bool:
    from infra.db.adapter import IS_CLOUD
    from infra.db.adapter import db_table_exists as _db_table_exists

    if IS_CLOUD:
        return _db_table_exists(conn, table_name)
    row = conn.execute(
        f"SELECT name FROM sqlite_master WHERE type='table' AND name = {PLACEHOLDER} LIMIT 1",
        (table_name,),
    ).fetchone()
    return row is not None


def _table_columns(conn, table_name: str) -> set[str]:
    from infra.db.adapter import IS_CLOUD
    from infra.db.adapter import db_table_columns as _db_table_columns

    if IS_CLOUD:
        return _db_table_columns(conn, table_name)
    if not _table_exists(conn, table_name):
        return set()
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row["name"] for row in rows}


def _project_id_column(conn) -> str:
    from infra.db.adapter import IS_CLOUD

    if IS_CLOUD:
        return "project_id"
    cols = _table_columns(conn, "projects")
    return "project_id" if "project_id" in cols else "id"


def _project_time_columns(conn) -> tuple[str, str]:
    from infra.db.adapter import IS_CLOUD

    if IS_CLOUD:
        return "created_date", "updated_at"
    cols = _table_columns(conn, "projects")
    created_col = "created_at" if "created_at" in cols else "created_date"
    updated_col = "updated_at" if "updated_at" in cols else created_col
    return created_col, updated_col


def migrate_schema(conn: sqlite3.Connection) -> None:
    """Aplica migraciones idempotentes."""
    if _table_exists(conn, "projects"):
        project_cols = _table_columns(conn, "projects")
        if "loop_url" not in project_cols:
            conn.execute("ALTER TABLE projects ADD COLUMN loop_url TEXT")
        if "repo_url" not in project_cols:
            conn.execute("ALTER TABLE projects ADD COLUMN repo_url TEXT")
        if "artifacts_url" not in project_cols:
            conn.execute("ALTER TABLE projects ADD COLUMN artifacts_url TEXT")
        if "artifacts_type" not in project_cols:
            conn.execute("ALTER TABLE projects ADD COLUMN artifacts_type TEXT")
        if "tech_stack" not in project_cols:
            conn.execute("ALTER TABLE projects ADD COLUMN tech_stack TEXT")

    if _table_exists(conn, "project_notes"):
        notes_cols = _table_columns(conn, "project_notes")
        if "entry_group_id" not in notes_cols:
            conn.execute("ALTER TABLE project_notes ADD COLUMN entry_group_id TEXT")
        if "note_title" not in notes_cols:
            conn.execute("ALTER TABLE project_notes ADD COLUMN note_title TEXT")
        if "progress_percent" not in notes_cols:
            conn.execute("ALTER TABLE project_notes ADD COLUMN progress_percent INTEGER")
        if "estimated_end_date" not in notes_cols:
            conn.execute("ALTER TABLE project_notes ADD COLUMN estimated_end_date TEXT")


def _create_views(conn: sqlite3.Connection) -> None:
    """Crea vistas para ultima nota global y ultima nota por tipo."""
    conn.execute("DROP VIEW IF EXISTS v_project_latest_notes")
    conn.execute("DROP VIEW IF EXISTS v_project_last_note")
    conn.execute("DROP VIEW IF EXISTS v_project_progress_history")

    try:
        conn.execute("""
            CREATE VIEW v_project_latest_notes AS
            SELECT
                note_id, project_id, note_type, note_text, note_title, author, tags,
                is_private, created_at, entry_group_id, progress_percent, estimated_end_date
            FROM (
                SELECT
                    pn.*,
                    ROW_NUMBER() OVER (
                        PARTITION BY pn.project_id, pn.note_type
                        ORDER BY datetime(pn.created_at) DESC, pn.note_id DESC
                    ) AS rn
                FROM project_notes pn
            )
            WHERE rn = 1
            """)
        conn.execute("""
            CREATE VIEW v_project_last_note AS
            SELECT
                note_id, project_id, note_type, note_text, note_title, author, tags,
                is_private, created_at, entry_group_id, progress_percent, estimated_end_date
            FROM (
                SELECT
                    pn.*,
                    ROW_NUMBER() OVER (
                        PARTITION BY pn.project_id
                        ORDER BY datetime(pn.created_at) DESC, pn.note_id DESC
                    ) AS rn
                FROM project_notes pn
            )
            WHERE rn = 1
            """)
    except sqlite3.OperationalError:
        conn.execute("""
            CREATE VIEW v_project_latest_notes AS
            SELECT
                pn.note_id, pn.project_id, pn.note_type, pn.note_text, pn.note_title,
                pn.author, pn.tags, pn.is_private, pn.created_at, pn.entry_group_id,
                pn.progress_percent, pn.estimated_end_date
            FROM project_notes pn
            JOIN (
                SELECT project_id, note_type, MAX(datetime(created_at)) AS max_created_at
                FROM project_notes
                GROUP BY project_id, note_type
            ) mx
              ON mx.project_id = pn.project_id
             AND mx.note_type = pn.note_type
             AND datetime(mx.max_created_at) = datetime(pn.created_at)
            WHERE pn.note_id = (
                SELECT MAX(p2.note_id)
                FROM project_notes p2
                WHERE p2.project_id = pn.project_id
                  AND p2.note_type = pn.note_type
                  AND datetime(p2.created_at) = datetime(pn.created_at)
            )
            """)
        conn.execute("""
            CREATE VIEW v_project_last_note AS
            SELECT
                pn.note_id, pn.project_id, pn.note_type, pn.note_text, pn.note_title,
                pn.author, pn.tags, pn.is_private, pn.created_at, pn.entry_group_id,
                pn.progress_percent, pn.estimated_end_date
            FROM project_notes pn
            JOIN (
                SELECT project_id, MAX(datetime(created_at)) AS max_created_at
                FROM project_notes
                GROUP BY project_id
            ) mx
              ON mx.project_id = pn.project_id
             AND datetime(mx.max_created_at) = datetime(pn.created_at)
            WHERE pn.note_id = (
                SELECT MAX(p2.note_id)
                FROM project_notes p2
                WHERE p2.project_id = pn.project_id
                  AND datetime(p2.created_at) = datetime(pn.created_at)
            )
            """)

    try:
        conn.execute("""
            CREATE VIEW v_project_progress_history AS
            SELECT
                x.project_id,
                x.note_id,
                x.entry_group_id,
                x.author,
                x.note_type,
                x.note_title,
                x.progress_percent,
                x.estimated_end_date,
                x.created_at
            FROM (
                SELECT
                    pn.*,
                    ROW_NUMBER() OVER (
                        PARTITION BY pn.project_id, COALESCE(NULLIF(pn.entry_group_id, ''), CAST(pn.note_id AS TEXT))
                        ORDER BY pn.note_id DESC
                    ) AS rn
                FROM project_notes pn
                WHERE pn.progress_percent IS NOT NULL
            ) x
            WHERE x.rn = 1
            ORDER BY x.project_id, datetime(x.created_at) DESC, x.note_id DESC
            """)
    except sqlite3.OperationalError:
        conn.execute("""
            CREATE VIEW v_project_progress_history AS
            SELECT
                pn.project_id,
                pn.note_id,
                pn.entry_group_id,
                pn.author,
                pn.note_type,
                pn.note_title,
                pn.progress_percent,
                pn.estimated_end_date,
                pn.created_at
            FROM project_notes pn
            WHERE pn.progress_percent IS NOT NULL
            """)


def ensure_schema(conn: sqlite3.Connection) -> None:
    """Crea esquema base y aplica migraciones/vistas."""
    from infra.db.adapter import IS_CLOUD

    if IS_CLOUD:
        return  # Schema ya existe en Supabase
    conn.execute("""
        CREATE TABLE IF NOT EXISTS project_notes (
            note_id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT NOT NULL,
            note_text TEXT NOT NULL,
            note_type TEXT NOT NULL,
            author TEXT NOT NULL,
            tags TEXT,
            is_private INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            entry_group_id TEXT,
            note_title TEXT,
            progress_percent INTEGER,
            estimated_end_date TEXT
        )
        """)
    if _table_exists(conn, "project_notes"):
        notes_cols = _table_columns(conn, "project_notes")
        if "progress_percent" not in notes_cols:
            conn.execute("ALTER TABLE project_notes ADD COLUMN progress_percent INTEGER")
        if "estimated_end_date" not in notes_cols:
            conn.execute("ALTER TABLE project_notes ADD COLUMN estimated_end_date TEXT")
    migrate_schema(conn)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_project_notes_pid_date ON project_notes(project_id, created_at DESC)")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_project_notes_pid_type_date ON project_notes(project_id, note_type, created_at DESC)"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_project_notes_type ON project_notes(note_type)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_project_notes_tags ON project_notes(tags)")
    _create_views(conn)
    conn.commit()


def fetch_projects(conn: sqlite3.Connection, eligible_statuses: tuple[str, ...]) -> list[Project]:
    """Lee proyectos desde `projects` filtrando por status."""
    if not eligible_statuses or not _table_exists(conn, "projects"):
        return []

    cols = _table_columns(conn, "projects")
    id_col = _project_id_column(conn)
    created_col, updated_col = _project_time_columns(conn)
    owner_expr = "owner" if "owner" in cols else "''"
    country_expr = "country" if "country" in cols else "''"
    status_expr = "status" if "status" in cols else "''"
    loop_expr = "loop_url" if "loop_url" in cols else "''"
    repo_expr = "repo_url" if "repo_url" in cols else "''"
    artifacts_expr = "artifacts_url" if "artifacts_url" in cols else "''"
    artifacts_type_expr = "artifacts_type" if "artifacts_type" in cols else "''"
    tech_stack_expr = "tech_stack" if "tech_stack" in cols else "''"

    from infra.db.adapter import IS_CLOUD

    placeholders = ",".join([PLACEHOLDER] * len(eligible_statuses))
    # En PostgreSQL los campos timestamp no admiten COALESCE con ''; usar CAST explícito.
    if IS_CLOUD:
        created_expr_sel = f"COALESCE(CAST({created_col} AS TEXT), '') AS created_at"
        updated_expr_sel = f"COALESCE(CAST({updated_col} AS TEXT), '') AS updated_at"
        order_by = (
            f"ORDER BY COALESCE(CAST({updated_col} AS TEXT), '') DESC, COALESCE(CAST({created_col} AS TEXT), '') DESC"
        )
    else:
        created_expr_sel = f"COALESCE({created_col}, '') AS created_at"
        updated_expr_sel = f"COALESCE({updated_col}, '') AS updated_at"
        order_by = f"ORDER BY COALESCE({updated_col}, '') DESC, COALESCE({created_col}, '') DESC"
    query = f"""
        SELECT
            {id_col} AS project_id,
            COALESCE(name, '') AS name,
            COALESCE({status_expr}, '') AS status,
            COALESCE({owner_expr}, '') AS owner,
            COALESCE({country_expr}, '') AS country,
            {created_expr_sel},
            {updated_expr_sel},
            COALESCE({loop_expr}, '') AS loop_url,
            COALESCE({repo_expr}, '') AS repo_url,
            COALESCE({artifacts_expr}, '') AS artifacts_url,
            COALESCE({artifacts_type_expr}, '') AS artifacts_type,
            COALESCE({tech_stack_expr}, '') AS tech_stack
        FROM projects
        WHERE status IN ({placeholders})
        {order_by}
    """
    rows = conn.execute(query, tuple(eligible_statuses)).fetchall()
    return [
        Project(
            project_id=row["project_id"],
            name=row["name"],
            status=row["status"],
            owner=row["owner"],
            country=row["country"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            loop_url=row["loop_url"],
            repo_url=row["repo_url"],
            artifacts_url=row["artifacts_url"],
            artifacts_type=row["artifacts_type"],
            tech_stack=row["tech_stack"],
        )
        for row in rows
    ]


def upsert_project_loop_url(conn: sqlite3.Connection, project_id: str, loop_url: str) -> None:
    """Actualiza loop_url en projects para un proyecto."""
    cols = _table_columns(conn, "projects")
    if "loop_url" not in cols:
        conn.execute("ALTER TABLE projects ADD COLUMN loop_url TEXT")
    conn.execute(
        f"UPDATE projects SET loop_url = {PLACEHOLDER} WHERE id = {PLACEHOLDER} OR project_id = {PLACEHOLDER}",
        (loop_url.strip(), project_id.strip(), project_id.strip()),
    )
    conn.commit()


def upsert_project_links(
    conn: sqlite3.Connection,
    project_id: str,
    *,
    loop_url: str | None = None,
    repo_url: str | None = None,
    artifacts_url: str | None = None,
    artifacts_type: str | None = None,
    tech_stack: str | None = None,
) -> None:
    cols = _table_columns(conn, "projects")
    updates: list[str] = []
    params: list[Any] = []
    mapping = {
        "loop_url": loop_url,
        "repo_url": repo_url,
        "artifacts_url": artifacts_url,
        "artifacts_type": artifacts_type,
        "tech_stack": tech_stack,
    }
    for col, value in mapping.items():
        if col in cols and value is not None:
            updates.append(f"{col} = {PLACEHOLDER}")
            params.append(str(value).strip())
    if not updates:
        return
    params.extend([project_id.strip(), project_id.strip()])
    conn.execute(
        f"UPDATE projects SET {', '.join(updates)} WHERE id = {PLACEHOLDER} OR project_id = {PLACEHOLDER}",
        params,
    )
    conn.commit()


def _artifacts_type_label(code: str) -> str:
    return t(f"artifacts_type_{code}")


def _tech_stack_label(code: str) -> str:
    return t(f"tech_stack_{code}")


from infra.db_migrations import (  # noqa: E402
    add_project_member,
    ensure_members_schema,
    get_all_known_members,
    get_project_members,
    remove_project_member,
    update_project_status,
)


def insert_notes_batch(conn: sqlite3.Connection, notes: list[dict[str, Any]]) -> list[int]:
    """Inserta lote de notas inmutables. Retorna note_ids insertados."""
    from infra.db.adapter import db_now

    now = db_now()
    cleaned: list[tuple[Any, ...]] = []
    for note in notes:
        note_type = str(note.get("note_type", "")).strip()
        note_text = str(note.get("note_text", "")).strip()
        author = str(note.get("author", "")).strip()
        progress_percent = note.get("progress_percent")
        if progress_percent in ("", None):
            progress_percent = None
        elif not isinstance(progress_percent, int):
            raise ValueError("progress_percent debe ser entero entre 0 y 100.")
        if progress_percent is not None and not (0 <= progress_percent <= 100):
            raise ValueError("progress_percent debe estar entre 0 y 100.")
        if note_type not in NOTE_TYPES and note_type != POST_CLOSURE_TYPE:
            continue
        if not note_text or not author:
            continue
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
                note.get("effort_hours"),
                now,
            )
        )

    if not cleaned:
        return []

    from infra.db.adapter import IS_CLOUD

    placeholders_str = ", ".join([PLACEHOLDER] * 12)
    conn.executemany(
        f"""
        INSERT INTO project_notes
            (project_id, note_text, note_type, author, tags, is_private, entry_group_id, note_title,
             progress_percent, estimated_end_date, effort_hours, created_at)
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


def get_latest_notes_by_type(conn: sqlite3.Connection, project_id: str) -> dict[str, dict[str, Any] | None]:
    """Obtiene la ultima nota por tipo para un proyecto."""
    from infra.db.adapter import IS_CLOUD

    if IS_CLOUD:
        sql = f"""
            SELECT DISTINCT ON (note_type)
                note_type, note_text, note_title, author, tags, created_at
            FROM project_notes
            WHERE project_id = {PLACEHOLDER}
            ORDER BY note_type, created_at DESC, note_id DESC
        """
    else:
        sql = f"""
            SELECT note_type, note_text, note_title, author, tags, created_at
            FROM v_project_latest_notes
            WHERE project_id = {PLACEHOLDER}
        """
    rows = conn.execute(sql, (project_id,)).fetchall()
    by_type = {t: None for t in NOTE_TYPES}
    for row in rows:
        by_type[row["note_type"]] = dict(row)
    return by_type


def query_notes(
    conn: sqlite3.Connection,
    *,
    project_id: str | None = None,
    text_query: str | None = None,
    tag_contains: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    note_type: str | None = None,
    limit: int = 200,
) -> pd.DataFrame:
    """Consulta notas con filtros opcionales combinables."""
    sql = """
        SELECT
            note_id, project_id, note_type, note_title, author, tags, is_private, note_text, created_at, entry_group_id,
            progress_percent, estimated_end_date
        FROM project_notes
        WHERE 1=1
    """
    params: list[Any] = []

    if project_id:
        sql += f" AND project_id = {PLACEHOLDER}"
        params.append(project_id.strip())
    if text_query:
        sql += f" AND (note_text LIKE {PLACEHOLDER} OR note_title LIKE {PLACEHOLDER})"
        pattern = f"%{text_query.strip()}%"
        params.extend([pattern, pattern])
    if tag_contains:
        sql += f" AND tags LIKE {PLACEHOLDER}"
        params.append(f"%{tag_contains.strip()}%")
    if note_type and note_type in NOTE_TYPES:
        sql += f" AND note_type = {PLACEHOLDER}"
        params.append(note_type)
    from infra.db.adapter import IS_CLOUD

    date_fn = "" if IS_CLOUD else "date"
    order_fn = "" if IS_CLOUD else "datetime"

    if date_from:
        sql += (
            f" AND {date_fn}(created_at) >= {date_fn}({PLACEHOLDER})"
            if not IS_CLOUD
            else f" AND created_at::date >= {PLACEHOLDER}::date"
        )
        params.append(date_from.isoformat())
    if date_to:
        sql += (
            f" AND {date_fn}(created_at) <= {date_fn}({PLACEHOLDER})"
            if not IS_CLOUD
            else f" AND created_at::date <= {PLACEHOLDER}::date"
        )
        params.append(date_to.isoformat())

    if IS_CLOUD:
        sql += f" ORDER BY created_at DESC, note_id DESC LIMIT {PLACEHOLDER}"
    else:
        sql += f" ORDER BY {order_fn}(created_at) DESC, note_id DESC LIMIT {PLACEHOLDER}"
    params.append(int(limit))

    return db_read_dataframe(conn, sql, params=params)


def _parse_tags(raw: str) -> list[str]:
    parts = [item.strip() for item in raw.split(",")]
    return [p for p in parts if p]


def _merge_tags(selected_tags: list[str], csv_tags: str) -> str:
    merged: list[str] = []
    for tag in selected_tags + _parse_tags(csv_tags):
        if tag not in merged:
            merged.append(tag)
    return ",".join(merged)


def _get_recent_tags(conn: sqlite3.Connection, limit_rows: int = 300, max_tags: int = 40) -> list[str]:
    from infra.db.adapter import IS_CLOUD

    if IS_CLOUD:
        sql = (
            f"SELECT tags FROM project_notes WHERE COALESCE(tags,'') <> '' ORDER BY created_at DESC LIMIT {PLACEHOLDER}"
        )
    else:
        sql = f"SELECT tags FROM project_notes WHERE COALESCE(tags,'') <> '' ORDER BY datetime(created_at) DESC LIMIT {PLACEHOLDER}"
    rows = conn.execute(sql, (int(limit_rows),)).fetchall()
    tags: list[str] = []
    for row in rows:
        for tag in _parse_tags(str(row["tags"])):
            if tag not in tags:
                tags.append(tag)
            if len(tags) >= max_tags:
                return tags
    return tags


def _latest_project_note(conn: sqlite3.Connection, project_id: str) -> dict[str, Any] | None:
    from infra.db.adapter import IS_CLOUD

    if IS_CLOUD:
        sql = f"""
            SELECT note_id, note_type, note_title, note_text, author, tags, created_at, progress_percent, estimated_end_date
            FROM project_notes
            WHERE project_id = {PLACEHOLDER}
            ORDER BY created_at DESC, note_id DESC
            LIMIT 1
        """
    else:
        sql = f"""
            SELECT note_id, note_type, note_title, note_text, author, tags, created_at, progress_percent, estimated_end_date
            FROM v_project_last_note
            WHERE project_id = {PLACEHOLDER}
            LIMIT 1
        """
    row = conn.execute(sql, (project_id,)).fetchone()
    return dict(row) if row else None


def _get_project_hours(conn: sqlite3.Connection, project_id: str) -> dict[str, float]:
    """Retorna dev_hours y post_hours para un proyecto."""
    from infra.db.adapter import IS_CLOUD

    if IS_CLOUD:
        date_cmp = "pn.created_at <= p.closed_at"
    else:
        date_cmp = "datetime(pn.created_at) <= datetime(p.closed_at)"

    # Si "id" no existe (PostgreSQL solo tiene project_id), usar project_id dos veces no causa problema
    id_filter = f"p.project_id = {PLACEHOLDER}"
    if not IS_CLOUD:
        id_filter = f"p.project_id = {PLACEHOLDER} OR p.id = {PLACEHOLDER}"

    sql = f"""
        SELECT
            COALESCE(SUM(CASE
                WHEN pn.note_type != 'soporte_post_entrega'
                 AND (p.closed_at IS NULL OR {date_cmp})
                THEN pn.effort_hours ELSE 0
            END), 0) AS dev_hours,
            COALESCE(SUM(CASE
                WHEN pn.note_type = 'soporte_post_entrega'
                THEN pn.effort_hours ELSE 0
            END), 0) AS post_hours
        FROM projects p
        LEFT JOIN project_notes pn ON pn.project_id = p.project_id
        WHERE {id_filter}
    """
    params = (project_id,) if IS_CLOUD else (project_id, project_id)
    row = conn.execute(sql, params).fetchone()
    if row is None:
        return {"dev_hours": 0.0, "post_hours": 0.0}
    return {"dev_hours": float(row["dev_hours"]), "post_hours": float(row["post_hours"])}


def get_workload_df(conn: sqlite3.Connection, statuses: list[str]) -> pd.DataFrame:
    """Retorna DataFrame con carga por miembro: member_name, project_id, name, status, total_hours."""
    if not statuses:
        return pd.DataFrame(columns=["member_name", "project_id", "name", "status", "total_hours"])
    placeholders = ",".join([PLACEHOLDER] * len(statuses))
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
        LEFT JOIN project_notes pn ON pn.project_id = p.project_id AND pn.author = pm.member_name
        WHERE p.status IN ({placeholders})
        GROUP BY pm.member_name, p.project_id, p.name, p.status
        ORDER BY pm.member_name, total_hours DESC
        """,
        statuses,
    ).fetchall()
    if not rows:
        return pd.DataFrame(columns=["member_name", "project_id", "name", "status", "total_hours"])
    return pd.DataFrame([dict(r) for r in rows])


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


def _days_since(dt_str: str | None) -> int | None:
    if not dt_str:
        return None
    try:
        dt = pd.to_datetime(dt_str, errors="coerce")
        if pd.isna(dt):
            return None
        return max(0, (date.today() - dt.date()).days)
    except Exception:
        return None


def calculate_auto_progress(
    estimated_end_date: date | None,
    start_date: date | None = None,
) -> int | None:
    if not estimated_end_date:
        return None
    today = date.today()
    if estimated_end_date <= today:
        return 100
    if start_date is None or start_date >= today:
        return 0
    total_days = (estimated_end_date - start_date).days
    if total_days <= 0:
        return 100
    elapsed = (today - start_date).days
    return max(0, min(100, int(round((elapsed / total_days) * 100))))


def get_project_progress_trend(conn: sqlite3.Connection, project_id: str, *, limit: int = 50) -> pd.DataFrame:
    from infra.db.adapter import IS_CLOUD

    if IS_CLOUD:
        # DISTINCT ON deduplica por entry_group_id (un registro por sesión de entrada).
        # La subquery elige el más reciente por grupo; la query externa ordena
        # cronológicamente (DESC) para que el código de análisis obtenga los más
        # recientes primero (igual que la rama SQLite con v_project_progress_history).
        sql = f"""
            SELECT project_id, note_id, entry_group_id, author, note_type, note_title,
                   progress_percent, estimated_end_date, created_at
            FROM (
                SELECT DISTINCT ON (project_id, COALESCE(NULLIF(entry_group_id, ''), CAST(note_id AS TEXT)))
                    project_id, note_id, entry_group_id, author, note_type, note_title,
                    progress_percent, estimated_end_date, created_at
                FROM project_notes
                WHERE project_id = {PLACEHOLDER}
                  AND progress_percent IS NOT NULL
                ORDER BY project_id, COALESCE(NULLIF(entry_group_id, ''), CAST(note_id AS TEXT)),
                         created_at DESC, note_id DESC
            ) dedup
            ORDER BY created_at DESC, note_id DESC
            LIMIT {PLACEHOLDER}
        """
    else:
        sql = f"""
            SELECT
                project_id, note_id, entry_group_id, author, note_type, note_title,
                progress_percent, estimated_end_date, created_at
            FROM v_project_progress_history
            WHERE project_id = {PLACEHOLDER}
            ORDER BY datetime(created_at) DESC, note_id DESC
            LIMIT {PLACEHOLDER}
        """
    return db_read_dataframe(conn, sql, params=[project_id, int(limit)])


def _progress_trend_symbol(last_three: list[int]) -> str:
    if len(last_three) < 2:
        return "->"
    if last_three[0] > last_three[1]:
        return "↑"
    if last_three[0] < last_three[1]:
        return "↓"
    return "->"


def _clear_capture_saved_flag(project_id: str) -> None:
    st.session_state[f"ops_capture_saved_{project_id}"] = False


def _progress_cell_style(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    try:
        v = float(value)
    except Exception:
        return ""
    if v <= 39:
        return "background-color: #f8d7da; color: #721c24; font-weight: 700;"
    if v <= 79:
        return "background-color: #fff3cd; color: #856404; font-weight: 700;"
    return "background-color: #d4edda; color: #155724; font-weight: 700;"


def _progress_badge(value: Any) -> str:
    if value is None or pd.isna(value):
        return "Sin dato"
    try:
        v = int(float(value))
    except Exception:
        return "Sin dato"
    if v <= 39:
        return f"🟥 {v}%"
    if v <= 79:
        return f"🟨 {v}%"
    return f"🟩 {v}%"


def _resolve_default_author(
    candidate: str,
    all_members: list[str],
    fallback: str = "Xiomara Monroy",
) -> str:
    """Resuelve el nombre de autor para Captura rapida.

    Busca `candidate` en `all_members` con comparacion case-insensitive.
    Si hay match, devuelve el nombre exacto de la BD.
    Si no hay match y candidate no esta vacio, devuelve candidate tal cual.
    Si candidate esta vacio (o solo espacios), devuelve fallback.
    """
    stripped = candidate.strip()
    if not stripped:
        return fallback
    lower = stripped.lower()
    for member in all_members:
        if member.lower() == lower:
            return member
    return stripped


def get_executive_summary_df(
    conn: sqlite3.Connection,
    *,
    statuses: list[str] | None = None,
    search_query: str | None = None,
    min_days_without_update: int = 0,
) -> pd.DataFrame:
    """Resumen ejecutivo (1 fila por proyecto)."""
    if not _table_exists(conn, "projects"):
        return pd.DataFrame()

    if statuses is None or len(statuses) == 0:
        statuses = list(ONGOING_STATUSES)

    id_col = _project_id_column(conn)
    cols = _table_columns(conn, "projects")
    status_expr = "status" if "status" in cols else "''"
    loop_expr = "loop_url" if "loop_url" in cols else "''"
    repo_expr = "repo_url" if "repo_url" in cols else "''"
    artifacts_expr = "artifacts_url" if "artifacts_url" in cols else "''"

    from infra.db.adapter import IS_CLOUD

    placeholders = ",".join([PLACEHOLDER] * len(statuses))

    if IS_CLOUD:
        # PostgreSQL: usar DISTINCT ON para emular las vistas
        sql = f"""
            WITH last_note_per_project AS (
                SELECT DISTINCT ON (project_id)
                    project_id, note_text, created_at
                FROM project_notes
                ORDER BY project_id, created_at DESC, note_id DESC
            ),
            latest_general AS (
                SELECT DISTINCT ON (project_id) project_id, note_text
                FROM project_notes WHERE note_type = 'general'
                ORDER BY project_id, created_at DESC, note_id DESC
            ),
            latest_next AS (
                SELECT DISTINCT ON (project_id) project_id, note_text
                FROM project_notes WHERE note_type = 'proximo_paso'
                ORDER BY project_id, created_at DESC, note_id DESC
            ),
            latest_block AS (
                SELECT DISTINCT ON (project_id) project_id, note_text
                FROM project_notes WHERE note_type = 'bloqueador'
                ORDER BY project_id, created_at DESC, note_id DESC
            ),
            latest_risk AS (
                SELECT DISTINCT ON (project_id) project_id, note_text
                FROM project_notes WHERE note_type = 'riesgo'
                ORDER BY project_id, created_at DESC, note_id DESC
            ),
            latest_progress AS (
                SELECT DISTINCT ON (project_id) project_id, progress_percent, created_at
                FROM project_notes WHERE progress_percent IS NOT NULL
                ORDER BY project_id, created_at DESC, note_id DESC
            )
            SELECT
                p.{id_col} AS project_id,
                COALESCE(p.name, '') AS project_name,
                COALESCE(p.{status_expr}, '') AS status,
                COALESCE(p.{loop_expr}, '') AS loop_url,
                COALESCE(p.{repo_expr}, '') AS repo_url,
                COALESCE(p.{artifacts_expr}, '') AS artifacts_url,
                COALESCE(gg.note_text, ln.note_text, '') AS last_note,
                ln.created_at AS last_note_at,
                pp.note_text AS last_proximo_paso,
                bb.note_text AS last_bloqueador,
                rr.note_text AS last_riesgo,
                ph.progress_percent AS current_progress_percent,
                ph.created_at AS last_progress_at
            FROM projects p
            LEFT JOIN last_note_per_project ln ON ln.project_id = p.{id_col}
            LEFT JOIN latest_general gg ON gg.project_id = p.{id_col}
            LEFT JOIN latest_next pp ON pp.project_id = p.{id_col}
            LEFT JOIN latest_block bb ON bb.project_id = p.{id_col}
            LEFT JOIN latest_risk rr ON rr.project_id = p.{id_col}
            LEFT JOIN latest_progress ph ON ph.project_id = p.{id_col}
            WHERE p.{status_expr} IN ({placeholders})
            ORDER BY COALESCE(ln.created_at, NULL) DESC NULLS LAST, p.{id_col}
        """
    else:
        sql = f"""
            SELECT
                p.{id_col} AS project_id,
                COALESCE(p.name, '') AS project_name,
                COALESCE(p.{status_expr}, '') AS status,
                COALESCE(p.{loop_expr}, '') AS loop_url,
                COALESCE(p.{repo_expr}, '') AS repo_url,
                COALESCE(p.{artifacts_expr}, '') AS artifacts_url,
                COALESCE(gg.note_text, ln.note_text, '') AS last_note,
                ln.created_at AS last_note_at,
                pp.note_text AS last_proximo_paso,
                bb.note_text AS last_bloqueador,
                rr.note_text AS last_riesgo,
                ph.progress_percent AS current_progress_percent,
                ph.created_at AS last_progress_at
            FROM projects p
            LEFT JOIN v_project_last_note ln
                ON ln.project_id = p.{id_col}
            LEFT JOIN v_project_latest_notes gg
                ON gg.project_id = p.{id_col} AND gg.note_type = 'general'
            LEFT JOIN v_project_latest_notes pp
                ON pp.project_id = p.{id_col} AND pp.note_type = 'proximo_paso'
            LEFT JOIN v_project_latest_notes bb
                ON bb.project_id = p.{id_col} AND bb.note_type = 'bloqueador'
            LEFT JOIN v_project_latest_notes rr
                ON rr.project_id = p.{id_col} AND rr.note_type = 'riesgo'
            LEFT JOIN (
                SELECT h.project_id, h.progress_percent, h.created_at
                FROM v_project_progress_history h
                JOIN (
                    SELECT project_id, MAX(datetime(created_at)) AS max_created_at
                    FROM v_project_progress_history
                    GROUP BY project_id
                ) mx
                  ON mx.project_id = h.project_id
                 AND datetime(mx.max_created_at) = datetime(h.created_at)
            ) ph
                ON ph.project_id = p.{id_col}
            WHERE p.{status_expr} IN ({placeholders})
            ORDER BY COALESCE(ln.created_at, '') DESC, p.{id_col}
        """
    df = db_read_dataframe(conn, sql, params=statuses)
    if df.empty:
        return pd.DataFrame(
            columns=[
                "Project",
                "Status",
                "Days since last",
                "Last note",
                "Last proximo_paso",
                "Last bloqueador",
                "Last riesgo",
                "Current Progress %",
                "Last Progress Date",
                "Progress Trend",
                "Progress Delta",
                "Progress History",
                "Loop link",
                "Repo link",
                "Artifacts link",
                "Project ID",
            ]
        )

    df["Days since last"] = df["last_note_at"].apply(_days_since)
    df["Days since last"] = df["Days since last"].fillna(99999).astype(int)

    if search_query:
        q = search_query.strip().lower()
        if q:
            mask = (
                df["project_id"].astype(str).str.lower().str.contains(q, na=False)
                | df["project_name"].astype(str).str.lower().str.contains(q, na=False)
                | df["last_note"].astype(str).str.lower().str.contains(q, na=False)
                | df["last_proximo_paso"].astype(str).str.lower().str.contains(q, na=False)
                | df["last_bloqueador"].astype(str).str.lower().str.contains(q, na=False)
                | df["last_riesgo"].astype(str).str.lower().str.contains(q, na=False)
                | df["current_progress_percent"].astype(str).str.lower().str.contains(q, na=False)
            )
            df = df[mask]

    df = df[df["Days since last"] >= int(min_days_without_update)]

    progress_trends: list[str] = []
    progress_deltas: list[int | None] = []
    progress_histories: list[list[int]] = []
    for project_id in df["project_id"].tolist():
        p_hist_df = get_project_progress_trend(conn, project_id, limit=30)
        vals = [
            int(v) for v in p_hist_df["progress_percent"].tolist() if isinstance(v, (int, float)) and not pd.isna(v)
        ]
        last_three = vals[:3]
        progress_histories.append(vals[::-1] if vals else [])
        progress_trends.append(_progress_trend_symbol(last_three))
        if len(last_three) >= 2:
            progress_deltas.append(last_three[0] - last_three[1])
        else:
            progress_deltas.append(None)

    out = pd.DataFrame(
        {
            "Project": df["project_name"],
            "Status": df["status"].apply(lambda v: label_status(str(v))),
            "Days since last": df["Days since last"],
            "Last note": df["last_note"].fillna(""),
            "Last proximo_paso": df["last_proximo_paso"].fillna(""),
            "Last bloqueador": df["last_bloqueador"].fillna(""),
            "Last riesgo": df["last_riesgo"].fillna(""),
            "Current Progress %": df["current_progress_percent"],
            "Last Progress Date": df["last_progress_at"].fillna(""),
            "Progress Trend": progress_trends,
            "Progress Delta": progress_deltas,
            "Progress History": progress_histories,
            "Loop link": df["loop_url"].fillna(""),
            "Repo link": df["repo_url"].fillna(""),
            "Artifacts link": df["artifacts_url"].fillna(""),
            "Project ID": df["project_id"],
        }
    )
    out = out.sort_values(["Days since last", "Project"], ascending=[False, True]).reset_index(drop=True)
    return out


def _export_buttons(df: pd.DataFrame, prefix: str, label_suffix: str) -> None:
    if df.empty:
        return
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    json_bytes = df.to_json(orient="records", force_ascii=False, indent=2).encode("utf-8")
    col_csv, col_json = st.columns(2)
    with col_csv:
        st.download_button(
            label=f"{t('download_csv')} ({label_suffix})",
            data=csv_bytes,
            file_name=f"{prefix}.csv",
            mime="text/csv",
            key=f"dl_csv_{prefix}",
        )
    with col_json:
        st.download_button(
            label=f"{t('download_json')} ({label_suffix})",
            data=json_bytes,
            file_name=f"{prefix}.json",
            mime="application/json",
            key=f"dl_json_{prefix}",
        )


def seed_demo_data(conn: sqlite3.Connection) -> None:
    """Carga datos demo manteniendo compatibilidad con esquema existente."""
    try:
        if not _table_exists(conn, "projects"):
            st.warning(t("ops_projects_table_missing"))
            return

        cols = _table_columns(conn, "projects")
        id_col = _project_id_column(conn)
        created_col, updated_col = _project_time_columns(conn)

        count = conn.execute("SELECT COUNT(*) AS n FROM projects").fetchone()["n"]
        if count == 0 and {"name", "status"}.issubset(cols):
            base_row: dict[str, Any] = {
                id_col: "MX-XIOMY-0001",
                "name": "Demo Operativo 1",
                "status": "planning",
            }
            if "owner" in cols:
                base_row["owner"] = "XIOMY"
            if "country" in cols:
                base_row["country"] = "MX"
            if created_col in cols:
                base_row[created_col] = "2026-01-01T10:00:00"
            if updated_col in cols:
                base_row[updated_col] = "2026-01-01T10:00:00"
            if "loop_url" in cols:
                base_row["loop_url"] = "https://loop.microsoft.com"

            cols_sql = ", ".join(base_row.keys())
            vals_sql = ", ".join(["?"] * len(base_row))
            conn.execute(
                f"INSERT INTO projects ({cols_sql}) VALUES ({vals_sql})",
                tuple(base_row.values()),
            )

            base_row2 = dict(base_row)
            base_row2[id_col] = "MX-XIOMY-0002"
            base_row2["name"] = "Demo Operativo 2"
            base_row2["status"] = "implemented"
            conn.execute(
                f"INSERT INTO projects ({cols_sql}) VALUES ({vals_sql})",
                tuple(base_row2.values()),
            )

        n_notes = conn.execute("SELECT COUNT(*) AS n FROM project_notes").fetchone()["n"]
        if n_notes == 0:
            conn.execute("""
                INSERT INTO project_notes
                    (project_id, note_text, note_type, author, tags, is_private, entry_group_id, note_title)
                VALUES
                    ('MX-XIOMY-0001', 'Se valido backlog con Comercial y TI.', 'general', 'Xiomy', 'comercial,ti', 0, 'seedgrp1', 'Kickoff'),
                    ('MX-XIOMY-0001', 'Enviar briefing a TI - Responsable: Xiomy - Fecha: 2026-03-03.', 'proximo_paso', 'Xiomy', 'accion,ti', 0, 'seedgrp1', 'Kickoff'),
                    ('MX-XIOMY-0002', 'Riesgo de cambio de owner en area comercial.', 'riesgo', 'Xiomy', 'riesgo,owner', 0, 'seedgrp2', 'Riesgos iniciales')
                """)
        conn.commit()
        st.success(t("ops_demo_loaded"))
    except Exception as exc:
        st.error(f"{t('ops_demo_load_error')}: {exc}")


def _render_last_notes_cards(conn: sqlite3.Connection, project_id: str) -> None:
    st.subheader(t("ops_last_notes_title"))
    latest_by_type = get_latest_notes_by_type(conn, project_id)
    cols = st.columns(4)
    for idx, note_type in enumerate(NOTE_TYPES):
        data = latest_by_type.get(note_type)
        with cols[idx]:
            st.markdown(f"**{label_note_type(note_type)}**")
            if not data:
                st.caption(t("ops_no_note"))
                continue
            title_txt = f"{data.get('note_title', '').strip()} - " if data.get("note_title") else ""
            st.caption(f"{title_txt}{data.get('created_at', '')} - {data.get('author', t('na'))}")
            st.write(data.get("note_text", ""))
            progress_val = data.get("progress_percent")
            if progress_val is not None and not pd.isna(progress_val):
                st.caption(f"{t('ops_progress_percent_label')}: {int(progress_val)}%")
            if data.get("tags"):
                st.caption(f"{t('ops_tags_label')}: {data['tags']}")


def _render_capture_tab(conn: sqlite3.Connection) -> None:
    st.subheader(t("ops_quick_capture"))
    st.info(t("ops_capture_help_info"))

    selected_statuses = st.multiselect(
        t("ops_included_statuses"),
        options=list(ONGOING_STATUSES),
        format_func=label_status,
        default=list(CAPTURE_DEFAULT_STATUSES),
        key="ops_capture_statuses",
    )
    effective_statuses = tuple(selected_statuses) if selected_statuses else ONGOING_STATUSES
    projects = fetch_projects(conn, effective_statuses)
    if not projects:
        st.warning(t("ops_no_eligible_projects"))
        return

    options = {f"{p.project_id} - {p.name} ({label_status(p.status)})": p for p in projects}
    selected_label = st.selectbox(t("project_label"), list(options.keys()), key="ops_v2_project_select")
    selected_project = options[selected_label]

    latest_note = _latest_project_note(conn, selected_project.project_id)
    last_update_text = latest_note["created_at"] if latest_note else t("ops_no_notes")
    has_saved_loop_url = bool((selected_project.loop_url or "").strip())
    is_first_entry = latest_note is None
    latest_progress_df = get_project_progress_trend(conn, selected_project.project_id, limit=1)
    last_progress_value = None
    last_progress_date = None
    if not latest_progress_df.empty:
        last_progress_value = latest_progress_df.iloc[0]["progress_percent"]
        last_progress_date = latest_progress_df.iloc[0]["created_at"]

    info1, info2, info3 = st.columns([1, 1, 2])
    with info1:
        st.caption(t("status"))
        st.write(label_status(selected_project.status) if selected_project.status else t("na"))
    with info2:
        st.caption(t("ops_last_update"))
        st.write(last_update_text)
    with info3:
        st.caption(t("loop_label"))
        if has_saved_loop_url:
            st.link_button(t("open_loop_btn"), selected_project.loop_url)
            st.caption(selected_project.loop_url)
        else:
            st.write(t("no_link"))

    # Limpia confirmación pendiente si el proyecto ya no puede reabrirse
    _reopen_key = f"ops_confirm_reopen_{selected_project.project_id}"
    if (
        not can_transition(str(selected_project.status or ""), "executing")
        or str(selected_project.status or "").lower() != "implemented"
    ):
        st.session_state.pop(_reopen_key, None)

    # Botón de reapertura — visible solo para proyectos implementados
    if (
        can_transition(str(selected_project.status or ""), "executing")
        and str(selected_project.status or "").lower() == "implemented"
    ):
        confirm_reopen_key = _reopen_key
        st.info(
            "Este proyecto está **Implementado**. "
            "Si hay trabajo nuevo, puedes reabrirlo para seguir registrando avance."
        )
        if st.button(
            "🔓 Reabrir proyecto",
            key=f"ops_reopen_{selected_project.project_id}",
            help="Vuelve el proyecto a En Ejecución.",
        ):
            st.session_state[confirm_reopen_key] = True

        if st.session_state.get(confirm_reopen_key):
            st.warning(
                "⚠️ ¿Confirmas reapertura? "
                "El status volverá a **En ejecución** y podrás registrar nuevas notas normalmente."
            )
            c1, c2 = st.columns(2)
            if c1.button(
                "Sí, reabrir",
                key=f"ops_reopen_yes_{selected_project.project_id}",
                type="primary",
            ):
                try:
                    update_project_status(conn, selected_project.project_id, "executing")
                    st.session_state.pop(confirm_reopen_key, None)
                    st.success("✅ Proyecto reabierto. Ya puedes registrar nuevas notas.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Error al reabrir proyecto: {exc}")
            if c2.button("Cancelar", key=f"ops_reopen_no_{selected_project.project_id}"):
                st.session_state.pop(confirm_reopen_key, None)
                st.rerun()

    if last_progress_value is not None and not pd.isna(last_progress_value):
        st.caption(
            f"{t('ops_progress_last_value')}: {int(last_progress_value)}% ({t('ops_progress_last_date')}: {last_progress_date})"
        )
    else:
        st.caption(t("ops_progress_no_data"))

    links_col1, links_col2, links_col3 = st.columns(3)
    with links_col1:
        if selected_project.loop_url:
            st.link_button(t("open_loop_btn"), selected_project.loop_url, use_container_width=True)
    with links_col2:
        if selected_project.repo_url:
            st.link_button(t("open_repo_btn"), selected_project.repo_url, use_container_width=True)
    with links_col3:
        if selected_project.artifacts_url:
            st.link_button(t("open_artifacts_btn"), selected_project.artifacts_url, use_container_width=True)

    if is_first_entry:
        st.info(t("ops_first_entry_loop_required"))
    elif not has_saved_loop_url:
        st.warning(t("ops_loop_missing_warning"))

    links_expand_key = f"ops_links_expanded_{selected_project.project_id}"
    missing_links = not bool(selected_project.loop_url and selected_project.repo_url and selected_project.artifacts_url)
    if missing_links and st.button(t("configure_links"), key=f"ops_cfg_links_{selected_project.project_id}"):
        st.session_state[links_expand_key] = True

    with st.expander(t("project_links_section"), expanded=bool(st.session_state.get(links_expand_key, False))):
        c_link_1, c_link_2 = st.columns(2)
        with c_link_1:
            loop_url_input = st.text_input(
                t("loop_link"),
                value=selected_project.loop_url or "",
                key=f"ops_loop_url_{selected_project.project_id}",
            )
            repo_url_input = st.text_input(
                t("repo_link"),
                value=selected_project.repo_url or "",
                help=t("repo_help"),
                key=f"ops_repo_url_{selected_project.project_id}",
            )
            artifacts_url_input = st.text_input(
                t("artifacts_link"),
                value=selected_project.artifacts_url or "",
                help=t("artifacts_help"),
                key=f"ops_artifacts_url_{selected_project.project_id}",
            )
        with c_link_2:
            artifacts_type_input = st.selectbox(
                t("artifacts_type"),
                options=list(ARTIFACT_TYPES),
                index=(
                    list(ARTIFACT_TYPES).index(selected_project.artifacts_type)
                    if selected_project.artifacts_type in ARTIFACT_TYPES
                    else list(ARTIFACT_TYPES).index("other")
                ),
                format_func=_artifacts_type_label,
                key=f"ops_artifacts_type_{selected_project.project_id}",
            )
            tech_stack_input = st.selectbox(
                t("tech_stack"),
                options=list(TECH_STACK_OPTIONS),
                index=(
                    list(TECH_STACK_OPTIONS).index(selected_project.tech_stack)
                    if selected_project.tech_stack in TECH_STACK_OPTIONS
                    else list(TECH_STACK_OPTIONS).index("other")
                ),
                format_func=_tech_stack_label,
                key=f"ops_tech_stack_{selected_project.project_id}",
            )
            st.write("")
            st.write("")
            if st.button(
                t("save_links"), key=f"ops_save_links_{selected_project.project_id}", use_container_width=True
            ):
                try:
                    upsert_project_links(
                        conn,
                        selected_project.project_id,
                        loop_url=loop_url_input,
                        repo_url=repo_url_input,
                        artifacts_url=artifacts_url_input,
                        artifacts_type=artifacts_type_input,
                        tech_stack=tech_stack_input,
                    )
                    st.success(t("ops_links_updated"))
                    st.session_state[links_expand_key] = False
                    st.rerun()
                except Exception as exc:
                    st.error(f"{t('ops_link_save_error')}: {exc}")

    _render_members_section(conn, selected_project.project_id)

    _candidate = str(st.session_state.get("current_user", st.session_state.get("author", "")))
    _all_members = get_all_known_members(conn)
    default_author = _resolve_default_author(_candidate, _all_members)
    note_help = _note_type_help()
    note_example = _note_type_example()
    capture_saved_key = f"ops_capture_saved_{selected_project.project_id}"
    if capture_saved_key not in st.session_state:
        st.session_state[capture_saved_key] = False

    with st.form(key=f"ops_capture_form_{selected_project.project_id}", clear_on_submit=True):
        author = st.text_input(
            t("ops_author"),
            value=default_author,
            key=f"ops_author_{selected_project.project_id}",
        )
        enable_progress_capture = st.checkbox(
            t("ops_progress_capture_enable"),
            value=True,
            key=f"ops_enable_progress_{selected_project.project_id}",
        )
        default_progress = (
            int(last_progress_value) if last_progress_value is not None and not pd.isna(last_progress_value) else 0
        )
        progress_percent_input = st.number_input(
            t("ops_progress_percent_label"),
            min_value=0,
            max_value=100,
            value=default_progress,
            step=1,
            disabled=not enable_progress_capture,
            key=f"ops_progress_percent_{selected_project.project_id}",
        )
        estimated_end_date_input = st.date_input(
            t("ops_estimated_end_date_label"),
            value=None,
            key=f"ops_estimated_end_{selected_project.project_id}",
        )
        if isinstance(estimated_end_date_input, date):
            suggested_progress = calculate_auto_progress(estimated_end_date_input)
            if suggested_progress is not None:
                st.caption(f"{t('ops_progress_suggested')}: {suggested_progress}%")

        effort_hours_input = st.number_input(
            "Horas invertidas esta semana",
            min_value=0.0,
            max_value=80.0,
            value=0.0,
            step=0.5,
            key=f"ops_effort_hours_{selected_project.project_id}",
        )

        general = st.text_area(
            label_note_type("general"),
            placeholder=note_help["general"],
            height=120,
            key=f"ops_general_{selected_project.project_id}",
        )
        st.caption(f"{note_help['general']} {note_example['general']}")
        proximo_paso = st.text_area(
            label_note_type("proximo_paso"),
            placeholder=note_help["proximo_paso"],
            height=120,
            key=f"ops_next_{selected_project.project_id}",
        )
        st.caption(f"{note_help['proximo_paso']} {note_example['proximo_paso']}")
        bloqueador = st.text_area(
            label_note_type("bloqueador"),
            placeholder=note_help["bloqueador"],
            height=120,
            key=f"ops_blocker_{selected_project.project_id}",
        )
        st.caption(f"{note_help['bloqueador']} {note_example['bloqueador']}")
        riesgo = st.text_area(
            label_note_type("riesgo"),
            placeholder=note_help["riesgo"],
            height=120,
            key=f"ops_risk_{selected_project.project_id}",
        )
        st.caption(f"{note_help['riesgo']} {note_example['riesgo']}")
        c_btn, c_state = st.columns([1, 2])
        with c_btn:
            submitted = st.form_submit_button(t("ops_save_update_btn"), type="primary")
        with c_state:
            if st.session_state.get(capture_saved_key):
                st.success("Actualización guardada")

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

    # Limpia confirmación pendiente si el proyecto ya no puede cerrarse
    _close_key = f"ops_confirm_close_{selected_project.project_id}"
    if not can_transition(str(selected_project.status or ""), "implemented"):
        st.session_state.pop(_close_key, None)

    # Botón explícito para cerrar proyecto (executing → implemented)
    if can_transition(str(selected_project.status or ""), "implemented"):
        st.markdown("**Cierre de proyecto**")
        confirm_close_key = _close_key
        if st.button(
            "🔒 Cerrar proyecto",
            key=f"ops_close_{selected_project.project_id}",
            help="Marca el proyecto como Implementado. Acción reversible.",
        ):
            st.session_state[confirm_close_key] = True

        if st.session_state.get(confirm_close_key):
            st.warning(
                "⚠️ ¿Confirmas el cierre del proyecto? "
                "El status cambiará a **Implementado**. Puedes reabrirlo después si es necesario."
            )
            c1, c2 = st.columns(2)
            if c1.button(
                "Sí, cerrar",
                key=f"ops_close_yes_{selected_project.project_id}",
                type="primary",
            ):
                try:
                    update_project_status(conn, selected_project.project_id, "implemented")
                    st.session_state.pop(confirm_close_key, None)
                    st.success("✅ Proyecto cerrado correctamente.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Error al cerrar proyecto: {exc}")
            if c2.button("Cancelar", key=f"ops_close_no_{selected_project.project_id}"):
                st.session_state.pop(confirm_close_key, None)
                st.rerun()

    st.markdown("---")

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
                    insert_notes_batch(
                        conn,
                        [
                            {
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
                            }
                        ],
                    )
                    st.success("Actividad post-cierre registrada correctamente.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Error al guardar: {exc}")

    _render_last_notes_cards(conn, selected_project.project_id)

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


def _render_executive_tab(conn: sqlite3.Connection) -> None:
    st.subheader(t("ops_executive_summary"))

    all_projects = fetch_projects(conn, ONGOING_STATUSES)
    available_statuses = sorted({p.status for p in all_projects if p.status})
    default_statuses = available_statuses if available_statuses else list(ONGOING_STATUSES)

    c1, c2, c3 = st.columns([2, 2, 1])
    with c1:
        status_filter = st.multiselect(
            t("ops_states"),
            options=available_statuses if available_statuses else list(ONGOING_STATUSES),
            format_func=label_status,
            default=default_statuses,
            key="ops_exec_status_filter",
        )
    with c2:
        search_query = st.text_input(t("ops_search"), key="ops_exec_search")
    with c3:
        day_threshold = st.number_input(
            t("ops_days_without_update"),
            min_value=0,
            max_value=9999,
            value=0,
            step=1,
            key="ops_exec_days",
        )

    try:
        summary_df = get_executive_summary_df(
            conn,
            statuses=status_filter if status_filter else list(ONGOING_STATUSES),
            search_query=search_query or None,
            min_days_without_update=int(day_threshold),
        )
    except Exception as exc:
        st.error(f"{t('ops_summary_build_error')}: {exc}")
        return

    if summary_df.empty:
        st.info(t("ops_no_results_filters"))
        return

    summary_view = summary_df.copy()
    progress_numeric = pd.to_numeric(summary_view["Current Progress %"], errors="coerce")
    summary_view["% Avance"] = progress_numeric.apply(_progress_badge)
    if "Current Progress %" in summary_view.columns:
        summary_view = summary_view.drop(columns=["Current Progress %"])

    desired_order = ["Project", "% Avance"]
    remaining = [c for c in summary_view.columns if c not in ("Project", "% Avance", "Status")]
    desired_order.extend(remaining)
    if "Status" in summary_view.columns:
        desired_order.append("Status")
    summary_view = summary_view[desired_order]

    _export_buttons(summary_view, prefix="resumen_ejecutivo", label_suffix=t("ops_executive_summary"))

    # --- Botón generación de presentación ---
    _, col_pptx = st.columns([5, 1])
    with col_pptx:
        gen_btn = st.button(
            "📊 Generar presentación",
            key="btn_gen_pptx_exec",
            use_container_width=True,
        )

    if gen_btn:
        with st.spinner("Generando Resumen_Proyectos_Ejecucion.pptx..."):
            try:
                projects = SqliteDataSource().fetch_projects()
                if not projects:
                    st.warning("No hay proyectos en ejecución para incluir en la presentación.")
                else:
                    data = InMemoryDestination().save(_build_pptx_bytes(projects))
                    filename = f"Resumen_Proyectos_Ejecucion_{date.today()}.pptx"
                    # When a cloud destination returns a str URL, add isinstance(data, bytes) dispatch here.
                    st.download_button(
                        label=f"⬇ Descargar {filename}",
                        data=data,
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                        key=f"dl_pptx_exec_{filename}",
                    )
            except Exception as exc:
                st.error(f"Error al generar la presentación: {exc}")
    # --- fin botón presentación ---

    st.dataframe(
        summary_view,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Status": st.column_config.TextColumn(t("status")),
            "Last Progress Date": st.column_config.TextColumn(t("ops_progress_last_date")),
            "Progress Trend": st.column_config.TextColumn(t("ops_progress_trend")),
            "Loop link": st.column_config.LinkColumn(t("loop_label")),
            "Repo link": st.column_config.LinkColumn(t("repo_link")),
            "Artifacts link": st.column_config.LinkColumn(t("artifacts_link")),
        },
    )

    st.markdown("---")
    st.markdown(f"**{t('ops_progress_overview_title')}**")
    series_by_project: dict[str, list[int | None]] = {}
    max_points = 0
    for _, row in summary_df.iterrows():
        project_id = str(row.get("Project ID", ""))
        project_name = str(row.get("Project", project_id))
        history = row.get("Progress History") if isinstance(row.get("Progress History"), list) else []
        if history:
            label = f"{project_name} ({project_id})"
            series_by_project[label] = [int(v) if v is not None else None for v in history]
            max_points = max(max_points, len(history))

    if not series_by_project:
        st.info(t("ops_progress_no_data"))
    else:
        padded = {label: values + [None] * (max_points - len(values)) for label, values in series_by_project.items()}
        progress_compare_df = pd.DataFrame(padded)
        progress_compare_df.index = range(1, max_points + 1)
        st.caption("Comparativo de avance por proyecto en una sola vista.")
        st.line_chart(
            progress_compare_df,
            x_label="Registro",
            y_label=t("ops_progress_percent_label"),
            use_container_width=True,
        )

    _render_workload_section(conn, statuses=status_filter if status_filter else list(ONGOING_STATUSES))


def _render_cards(df: pd.DataFrame) -> None:
    grouped = df.copy()
    grouped["entry_group_id"] = grouped["entry_group_id"].fillna("").astype(str)
    grouped["group_key"] = grouped["entry_group_id"].where(
        grouped["entry_group_id"] != "", grouped["note_id"].astype(str)
    )

    for group_id, chunk in grouped.groupby("group_key", sort=False):
        first = chunk.iloc[0]
        with st.container(border=True):
            st.markdown(
                f"**{t('ops_update_title')} {group_id} - {first['created_at']} - {first.get('author') or t('na')} - {first['project_id']}**"
            )
            if first.get("tags"):
                st.caption(f"{t('ops_tags_label')}: {first['tags']}")
            progress_first = first.get("progress_percent")
            if progress_first is not None and not pd.isna(progress_first):
                st.caption(f"{t('ops_progress_percent_label')}: {int(first['progress_percent'])}%")
            for _, row in chunk.iterrows():
                title = str(row.get("note_title") or "").strip()
                title_prefix = f"{title} - " if title else ""
                st.markdown(f"- **{label_note_type(str(row['note_type']))}** {title_prefix}{row['note_text']}")


def _render_timeline_tab(conn: sqlite3.Connection) -> None:
    st.subheader(t("ops_timeline_history"))

    projects = fetch_projects(conn, ONGOING_STATUSES)
    options = {f"{p.project_id} - {p.name} ({label_status(p.status)})": p for p in projects}
    selected_label = st.selectbox(
        t("ops_project_timeline_select"),
        list(options.keys()) if options else [],
        key="ops_timeline_project_select",
    )
    selected_project_id = options[selected_label].project_id if selected_label else None

    col1, col2, col3 = st.columns(3)
    with col1:
        filter_text = st.text_input(t("ops_search_text"), key="ops_tl_text")
    with col2:
        filter_type = st.selectbox(
            t("ops_type"),
            options=["todos", *NOTE_TYPES],
            format_func=lambda x: t("ops_all") if x == "todos" else label_note_type(x),
            key="ops_tl_type",
        )
    with col3:
        limit = st.number_input(t("ops_limit"), min_value=10, max_value=2000, value=200, step=10, key="ops_tl_limit")

    d1, d2 = st.columns(2)
    with d1:
        date_from = st.date_input(t("ops_from"), value=None, key="ops_tl_from")
    with d2:
        date_to = st.date_input(t("ops_to"), value=None, key="ops_tl_to")

    note_type_filter = None if filter_type == "todos" else filter_type

    if selected_project_id:
        project_df = query_notes(
            conn,
            project_id=selected_project_id,
            text_query=filter_text or None,
            tag_contains=None,
            date_from=date_from if isinstance(date_from, date) else None,
            date_to=date_to if isinstance(date_to, date) else None,
            note_type=note_type_filter,
            limit=int(limit),
        )
    else:
        project_df = pd.DataFrame()

    st.markdown(f"**{t('ops_project_view')}**")
    if project_df.empty:
        st.info(t("ops_no_project_notes_filtered"))
    else:
        _export_buttons(
            project_df,
            prefix=f"timeline_{selected_project_id}",
            label_suffix=t("ops_project_timeline_label"),
        )
        _render_cards(project_df)

    st.markdown("---")
    st.markdown("<hr style='border: 3px solid #8a8f98; margin: 22px 0 12px 0;'>", unsafe_allow_html=True)
    st.markdown(f"**{t('ops_global_view')}**")
    global_df = query_notes(
        conn,
        project_id=None,
        text_query=filter_text or None,
        tag_contains=None,
        date_from=date_from if isinstance(date_from, date) else None,
        date_to=date_to if isinstance(date_to, date) else None,
        note_type=note_type_filter,
        limit=int(limit),
    )
    if global_df.empty:
        st.info(t("ops_no_global_notes_filtered"))
    else:
        _export_buttons(global_df, prefix="timeline_global", label_suffix=t("ops_global_timeline_label"))
        _render_cards(global_df)


def render_seguimiento_operativo() -> None:
    """Render principal de la pestana Seguimiento Operativo v2."""
    st.title(t("operational_log_tab"))
    st.caption(t("ops_tab_caption"))

    try:
        from infra.db.adapter import IS_CLOUD

        if not IS_CLOUD:
            with get_conn(DB_PATH) as conn:
                ensure_schema(conn)
                ensure_members_schema(conn)
    except Exception as exc:
        st.error(f"{t('ops_schema_init_error')}: {exc}")
        return

    with get_conn(DB_PATH) as conn:
        if st.checkbox(t("ops_load_demo"), value=False, key="ops_seed_demo_v2"):
            seed_demo_data(conn)
            st.rerun()

        tab_a, tab_b, tab_c = st.tabs([t("ops_quick_capture"), t("ops_executive_summary"), t("ops_timeline_history")])

        with tab_a:
            try:
                _render_capture_tab(conn)
            except Exception as exc:
                st.error(f"{t('ops_error_quick_capture')}: {exc}")

        with tab_b:
            try:
                _render_executive_tab(conn)
            except Exception as exc:
                st.error(f"{t('ops_error_executive_summary')}: {exc}")

        with tab_c:
            try:
                _render_timeline_tab(conn)
            except Exception as exc:
                st.error(f"{t('ops_error_timeline')}: {exc}")


if __name__ == "__main__":
    st.set_page_config(page_title="Seguimiento Operativo", page_icon=":pushpin:", layout="wide")
    render_seguimiento_operativo()
