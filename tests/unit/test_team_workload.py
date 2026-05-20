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
