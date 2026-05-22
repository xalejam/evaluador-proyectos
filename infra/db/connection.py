"""Conexión principal de base de datos — sqlite3 local o PostgreSQL en nube."""

from __future__ import annotations

from pathlib import Path

from infra.db.adapter import get_connection

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "project_viability.db"


def get_sqlite_conn(db_path: Path | str = DB_PATH):
    """Devuelve adaptador de conexión (sqlite3 local o psycopg2 en nube)."""
    return get_connection(local_path=str(db_path))
