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
    c.execute(
        "INSERT INTO project_notes (project_id, note_text, note_type, author, effort_hours) VALUES ('P1','x','general','Xiomara',10.0)"
    )
    c.execute(
        "INSERT INTO project_notes (project_id, note_text, note_type, author, effort_hours) VALUES ('P1','x','general','Xiomara',5.0)"
    )
    c.execute(
        "INSERT INTO project_notes (project_id, note_text, note_type, author, effort_hours) VALUES ('P2','x','general','Xiomara',20.0)"
    )
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
    conn_with_data.execute(
        "INSERT INTO projects (id, project_id, name, status) VALUES ('P9','P9','Sin miembros','executing')"
    )
    conn_with_data.commit()
    df = get_workload_df(conn_with_data, statuses=["executing"])
    # P9 no debe aparecer (no tiene miembros)
    assert "P9" not in df["project_id"].values


def test_workload_df_filters_by_status(conn_with_data):
    from ui.tabs.seguimiento_operativo import get_workload_df

    df = get_workload_df(conn_with_data, statuses=["executing"])
    # P3 es 'approved', no debe aparecer
    assert "P3" not in df["project_id"].values
