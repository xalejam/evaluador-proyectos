import sqlite3

from infra.db.migrations import ensure_schema


def test_ensure_schema_idempotent(temp_db_conn):
    # Primera corrida viene de fixture. Segunda no debe fallar.
    ensure_schema(temp_db_conn)

    projects_cols = {r["name"] for r in temp_db_conn.execute("PRAGMA table_info(projects)").fetchall()}
    notes_cols = {r["name"] for r in temp_db_conn.execute("PRAGMA table_info(project_notes)").fetchall()}

    assert "loop_url" in projects_cols
    assert "delivery_team" in projects_cols
    assert "updated_at" in projects_cols
    assert "entry_group_id" in notes_cols
    assert "note_title" in notes_cols
    assert "progress_percent" in notes_cols
    assert "estimated_end_date" in notes_cols


def test_ensure_schema_creates_evaluations_table(temp_db_conn):
    row = temp_db_conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='project_evaluations'"
    ).fetchone()
    assert row is not None
