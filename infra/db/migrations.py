"""Migraciones idempotentes centralizadas para project_viability.db."""

from __future__ import annotations

import sqlite3

from infra.db_migrations import (
    ensure_evaluations_schema as _ensure_evaluations_schema,
)
from infra.db_migrations import (
    ensure_notes_schema as _ensure_notes_schema,
)
from infra.db_migrations import (
    ensure_projects_schema as _ensure_projects_schema,
)


def ensure_projects_schema(conn: sqlite3.Connection) -> None:
    _ensure_projects_schema(conn)


def ensure_notes_schema(conn: sqlite3.Connection) -> None:
    _ensure_notes_schema(conn)


def ensure_evaluations_schema(conn: sqlite3.Connection) -> None:
    _ensure_evaluations_schema(conn)


def ensure_schema(conn: sqlite3.Connection) -> None:
    ensure_projects_schema(conn)
    ensure_notes_schema(conn)
    ensure_evaluations_schema(conn)
