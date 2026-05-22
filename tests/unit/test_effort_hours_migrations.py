import sqlite3

import pytest

from infra.db_migrations import ensure_notes_schema, ensure_projects_schema, update_project_status


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
