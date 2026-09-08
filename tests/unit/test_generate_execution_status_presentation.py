import sqlite3

from infra.db.adapter import get_connection
from scripts.generate_execution_status_presentation import (
    ProjectStatus,
    fetch_all_projects,
    fetch_executing_projects,
)

SCHEMA = """
CREATE TABLE projects (
    project_id TEXT PRIMARY KEY,
    name TEXT,
    status TEXT,
    description TEXT,
    closed_at TEXT,
    updated_at TEXT,
    created_date TEXT,
    hours_saved_per_month REAL
);
CREATE TABLE project_notes (
    note_id INTEGER PRIMARY KEY,
    project_id TEXT,
    note_type TEXT,
    note_text TEXT,
    created_at TEXT,
    progress_percent INTEGER
);
"""


def _seed(conn, projects, notes):
    conn.executescript(SCHEMA)
    for p in projects:
        conn.execute(
            "INSERT INTO projects (project_id, name, status, description, closed_at, updated_at, created_date, hours_saved_per_month) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            p,
        )
    for n in notes:
        conn.execute(
            "INSERT INTO project_notes (project_id, note_type, note_text, created_at, progress_percent) VALUES (?, ?, ?, ?, ?)",
            n,
        )
    conn.commit()


def test_fetch_all_projects_returns_every_row(tmp_path):
    db_path = str(tmp_path / "t.db")
    raw = sqlite3.connect(db_path)
    _seed(
        raw,
        [
            ("A", "Proyecto A", "implemented", "desc A", "2026-06-01", "2026-06-01", "2026-01-01", 10.0),
            ("B", "Proyecto B", "executing", "desc B", None, "2026-06-01", "2026-01-01", 0.0),
        ],
        [],
    )
    raw.close()

    conn = get_connection(local_path=db_path)
    rows = fetch_all_projects(conn)
    conn.close()

    assert len(rows) == 2
    assert rows[0]["project_id"] == "A"
    assert rows[0]["hours_saved_per_month"] == 10.0


def test_fetch_executing_projects_only_returns_executing_with_latest_note_and_progress(tmp_path):
    db_path = str(tmp_path / "t.db")
    raw = sqlite3.connect(db_path)
    _seed(
        raw,
        [
            ("A", "Proyecto A", "executing", "desc A", None, "2026-06-01", "2026-01-01", 0.0),
            ("B", "Proyecto B", "implemented", "desc B", "2026-06-01", "2026-06-01", "2026-01-01", 10.0),
        ],
        [
            ("A", "general", "nota vieja", "2026-08-01 00:00:00", 40),
            ("A", "general", "nota nueva", "2026-08-15 00:00:00", 70),
            ("A", "bloqueador", "bloqueo actual", "2026-08-10 00:00:00", None),
        ],
    )
    raw.close()

    conn = get_connection(local_path=db_path)
    rows = fetch_executing_projects(conn)
    conn.close()

    assert len(rows) == 1
    project = rows[0]
    assert isinstance(project, ProjectStatus)
    assert project.project_id == "A"
    assert project.progress_percent == 70
    assert project.general_note == "nota nueva"
    assert project.blocker == "bloqueo actual"
    assert project.risk == ""


def test_fetch_executing_projects_returns_empty_list_when_none_executing(tmp_path):
    db_path = str(tmp_path / "t.db")
    raw = sqlite3.connect(db_path)
    _seed(raw, [("A", "Proyecto A", "implemented", "desc A", "2026-06-01", "2026-06-01", "2026-01-01", 10.0)], [])
    raw.close()

    conn = get_connection(local_path=db_path)
    rows = fetch_executing_projects(conn)
    conn.close()

    assert rows == []
