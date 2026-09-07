import sqlite3

from infra.presentation_ports import SqliteDataSource

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
    entry_group_id TEXT,
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
            "INSERT INTO project_notes (project_id, entry_group_id, note_type, note_text, created_at, progress_percent) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            n,
        )
    conn.commit()


def test_fetch_projects_does_not_turn_missing_progress_date_into_nan_string(tmp_path):
    # Un proyecto executing SIN ninguna nota de progreso, mezclado con uno
    # que SI tiene — es la combinacion que hace que pandas convierta el
    # hueco en float('nan') en vez de None (regresion: 'Invalid isoformat
    # string: nan' al generar la presentacion desde el boton de Streamlit).
    db_path = str(tmp_path / "t.db")
    raw = sqlite3.connect(db_path)
    _seed(
        raw,
        [
            ("A", "Sin notas", "executing", "desc A", None, "2026-06-01", "2026-01-01", 0.0),
            ("B", "Con notas", "executing", "desc B", None, "2026-06-01", "2026-01-01", 0.0),
        ],
        [
            ("B", "g1", "general", "avanzando", "2026-08-15 00:00:00", 70),
        ],
    )
    raw.close()

    projects = SqliteDataSource(db_path=db_path).fetch_projects()

    by_id = {p.project_id: p for p in projects}
    assert by_id["A"].progress_at is None
    assert by_id["B"].progress_at == "2026-08-15 00:00:00"


def test_fetch_all_projects_returns_full_portfolio(tmp_path):
    db_path = str(tmp_path / "t.db")
    raw = sqlite3.connect(db_path)
    _seed(
        raw,
        [
            ("A", "Cerrado", "implemented", "desc A", "2026-06-01", "2026-06-01", "2026-01-01", 100.0),
            ("B", "Activo", "executing", "desc B", None, "2026-06-01", "2026-01-01", 0.0),
        ],
        [],
    )
    raw.close()

    rows = SqliteDataSource(db_path=db_path).fetch_all_projects()

    assert {r["project_id"] for r in rows} == {"A", "B"}
