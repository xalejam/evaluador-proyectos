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
