"""Migraciones idempotentes para SQLite (local) y PostgreSQL (nube)."""

from __future__ import annotations

from typing import Iterable

from infra.db.adapter import get_connection, IS_CLOUD, PLACEHOLDER

DB_PATH = "project_viability.db"


def get_conn(db_path: str = DB_PATH):
    return get_connection(local_path=db_path)


def _table_exists(conn, table_name: str) -> bool:
    if IS_CLOUD:
        row = conn.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name=%s LIMIT 1",
            (table_name,),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
            (table_name,),
        ).fetchone()
    return row is not None


def _table_columns(conn, table_name: str) -> set[str]:
    if not _table_exists(conn, table_name):
        return set()
    if IS_CLOUD:
        rows = conn.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema='public' AND table_name=%s",
            (table_name,),
        ).fetchall()
        return {r[0] for r in rows}
    else:
        rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        return {row[1] for row in rows}


def _add_column_if_missing(conn, table: str, column_def: str) -> None:
    col_name = column_def.strip().split()[0]
    if col_name not in _table_columns(conn, table):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column_def}")


def _ensure_index(conn, sql: str) -> None:
    conn.execute(sql)


def _ensure_projects_base_table(conn) -> None:
    """Crea projects con esquema compatible si no existe."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            project_id TEXT,
            name TEXT,
            description TEXT,
            created_date TEXT,
            status TEXT,
            last_tracking_update TEXT,
            country TEXT,
            owner TEXT,
            current_time_per_task REAL,
            tasks_per_month INTEGER,
            staff_count INTEGER,
            avg_salary_per_hour REAL,
            time_reduction_percent REAL,
            development_hours REAL,
            development_cost_per_hour REAL,
            maintenance_monthly REAL,
            implementation_complexity INTEGER,
            risk_level INTEGER,
            viability_score REAL,
            priority TEXT,
            monthly_savings REAL,
            annual_savings REAL,
            payback_period_months REAL,
            roi_first_year REAL,
            recommendation TEXT,
            initial_development_cost REAL,
            hours_saved_per_month REAL,
            actual_monthly_savings REAL,
            actual_annual_savings REAL,
            loop_url TEXT,
            repo_url TEXT,
            artifacts_url TEXT,
            artifacts_type TEXT,
            tech_stack TEXT,
            delivery_team TEXT,
            updated_at TEXT DEFAULT (datetime('now'))
        )
        """
    )


def ensure_projects_schema(conn) -> None:
    """Asegura columnas y defaults necesarios en projects."""
    from infra.db.adapter import IS_CLOUD
    if IS_CLOUD:
        return
    _ensure_projects_base_table(conn)

    _add_column_if_missing(conn, "projects", "project_id TEXT")
    _add_column_if_missing(conn, "projects", "status TEXT")
    _add_column_if_missing(conn, "projects", "loop_url TEXT")
    _add_column_if_missing(conn, "projects", "repo_url TEXT")
    _add_column_if_missing(conn, "projects", "artifacts_url TEXT")
    _add_column_if_missing(conn, "projects", "artifacts_type TEXT")
    _add_column_if_missing(conn, "projects", "tech_stack TEXT")
    _add_column_if_missing(conn, "projects", "delivery_team TEXT")

    # SQLite puede fallar al agregar default expresion en ALTER; fallback sin default.
    if "updated_at" not in _table_columns(conn, "projects"):
        try:
            conn.execute("ALTER TABLE projects ADD COLUMN updated_at TEXT DEFAULT (datetime('now'))")
        except Exception:
            conn.execute("ALTER TABLE projects ADD COLUMN updated_at TEXT")

    # Compatibilidad: espejar id -> project_id cuando falte.
    conn.execute(
        """
        UPDATE projects
        SET project_id = id
        WHERE COALESCE(project_id, '') = '' AND COALESCE(id, '') <> ''
        """
    )
    conn.execute(
        """
        UPDATE projects
        SET updated_at = datetime('now')
        WHERE COALESCE(updated_at, '') = ''
        """
    )
    _add_column_if_missing(conn, "projects", "closed_at TEXT")
    conn.commit()


def ensure_evaluations_schema(conn) -> None:
    """Tabla append-only para historial de evaluaciones."""
    from infra.db.adapter import IS_CLOUD
    if IS_CLOUD:
        return
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS project_evaluations (
            evaluation_id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            created_by TEXT,
            action TEXT NOT NULL,
            status_after TEXT,
            score_total REAL,
            score_impact REAL,
            score_risk REAL,
            score_complexity REAL,
            monthly_savings REAL,
            annual_savings REAL,
            payback_period_months REAL,
            roi_first_year REAL,
            hours_saved_per_month REAL,
            inputs_json TEXT,
            answers_json TEXT,
            weights_json TEXT,
            impact_score REAL,
            effort_score REAL,
            is_current INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    # Idempotent migrations for DBs created before consolidation
    _add_column_if_missing(conn, "project_evaluations", "answers_json TEXT")
    _add_column_if_missing(conn, "project_evaluations", "weights_json TEXT")
    _add_column_if_missing(conn, "project_evaluations", "impact_score REAL")
    _add_column_if_missing(conn, "project_evaluations", "effort_score REAL")
    _add_column_if_missing(conn, "project_evaluations", "is_current INTEGER NOT NULL DEFAULT 0")
    _ensure_index(
        conn,
        "CREATE INDEX IF NOT EXISTS idx_eval_project_time ON project_evaluations(project_id, created_at)",
    )
    _ensure_index(
        conn,
        "CREATE INDEX IF NOT EXISTS idx_eval_current ON project_evaluations(project_id, is_current)",
    )
    conn.commit()


def _create_notes_views(conn) -> None:
    conn.execute("DROP VIEW IF EXISTS v_project_latest_notes")
    conn.execute("DROP VIEW IF EXISTS v_project_last_note")
    conn.execute("DROP VIEW IF EXISTS v_project_progress_history")

    try:
        conn.execute(
            """
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
            """
        )
        conn.execute(
            """
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
            """
        )
    except Exception:
        conn.execute(
            """
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
            """
        )
        conn.execute(
            """
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
            """
        )

    try:
        conn.execute(
            """
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
                        ORDER BY pn.note_id ASC
                    ) AS rn
                FROM project_notes pn
                WHERE pn.progress_percent IS NOT NULL
            ) x
            WHERE x.rn = 1
            ORDER BY x.project_id, datetime(x.created_at) DESC, x.note_id DESC
            """
        )
    except Exception:
        # Compatibilidad con engines viejos de SQLite sin funciones avanzadas.
        conn.execute(
            """
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
            """
        )


def ensure_notes_schema(conn) -> None:
    """Asegura esquema de notas inmutables + vistas."""
    from infra.db.adapter import IS_CLOUD
    if IS_CLOUD:
        return
    conn.execute(
        """
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
        """
    )
    _add_column_if_missing(conn, "project_notes", "entry_group_id TEXT")
    _add_column_if_missing(conn, "project_notes", "note_title TEXT")
    _add_column_if_missing(conn, "project_notes", "progress_percent INTEGER")
    _add_column_if_missing(conn, "project_notes", "estimated_end_date TEXT")
    _add_column_if_missing(conn, "project_notes", "effort_hours REAL")

    _ensure_index(
        conn,
        "CREATE INDEX IF NOT EXISTS idx_project_notes_pid_date ON project_notes(project_id, created_at DESC)",
    )
    _ensure_index(
        conn,
        "CREATE INDEX IF NOT EXISTS idx_project_notes_pid_type_date ON project_notes(project_id, note_type, created_at DESC)",
    )
    _ensure_index(conn, "CREATE INDEX IF NOT EXISTS idx_project_notes_type ON project_notes(note_type)")
    _ensure_index(conn, "CREATE INDEX IF NOT EXISTS idx_project_notes_tags ON project_notes(tags)")
    _create_notes_views(conn)
    conn.commit()


def update_project_status(conn, project_id: str, status: str) -> None:
    conn.execute(
        f"UPDATE projects SET status = {PLACEHOLDER}, updated_at = datetime('now') WHERE id = {PLACEHOLDER} OR project_id = {PLACEHOLDER}",
        (status.strip(), project_id.strip(), project_id.strip()),
    )
    if status.strip() == "implemented":
        conn.execute(
            f"""
            UPDATE projects
            SET closed_at = datetime('now')
            WHERE (id = {PLACEHOLDER} OR project_id = {PLACEHOLDER})
              AND (closed_at IS NULL OR closed_at = '')
            """,
            (project_id.strip(), project_id.strip()),
        )
    conn.commit()


def ensure_members_schema(conn) -> None:
    """Crea tabla project_members si no existe."""
    from infra.db.adapter import IS_CLOUD
    if IS_CLOUD:
        return
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


def get_project_members(conn, project_id: str) -> list[str]:
    """Retorna lista de nombres de miembros para un proyecto."""
    rows = conn.execute(
        f"SELECT member_name FROM project_members WHERE project_id = {PLACEHOLDER} ORDER BY added_at",
        (project_id,),
    ).fetchall()
    return [r[0] for r in rows]


def add_project_member(conn, project_id: str, member_name: str) -> None:
    """Agrega un miembro a un proyecto. Ignora duplicados silenciosamente."""
    conn.execute(
        f"INSERT OR IGNORE INTO project_members (project_id, member_name) VALUES ({PLACEHOLDER}, {PLACEHOLDER})",
        (project_id.strip(), member_name.strip()),
    )
    conn.commit()


def remove_project_member(conn, project_id: str, member_name: str) -> None:
    """Elimina un miembro de un proyecto."""
    conn.execute(
        f"DELETE FROM project_members WHERE project_id = {PLACEHOLDER} AND member_name = {PLACEHOLDER}",
        (project_id.strip(), member_name.strip()),
    )
    conn.commit()


def get_all_known_members(conn) -> list[str]:
    """Retorna todos los nombres de miembros únicos en toda la BD (para sugerencias)."""
    rows = conn.execute(
        "SELECT DISTINCT member_name FROM project_members ORDER BY member_name"
    ).fetchall()
    return [r[0] for r in rows]


def ensure_all_operational_schema(conn) -> None:
    """Atajo para asegurar esquemas de projects/evaluations/notes."""
    from infra.db.adapter import IS_CLOUD
    if IS_CLOUD:
        return  # Schema ya existe en Supabase, creado manualmente via SQL Editor
    ensure_projects_schema(conn)
    ensure_evaluations_schema(conn)
    ensure_notes_schema(conn)
    ensure_members_schema(conn)
