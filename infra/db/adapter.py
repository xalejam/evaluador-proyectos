"""Adaptador de conexión que unifica sqlite3 y psycopg2."""

from __future__ import annotations

import os
import sqlite3
from typing import Any

_DATABASE_URL = os.environ.get("DATABASE_URL", "")
IS_CLOUD = bool(_DATABASE_URL)
PLACEHOLDER = "%s" if IS_CLOUD else "?"


class _Psycopg2Adapter:
    """Envuelve una conexión psycopg2 con la misma interfaz que sqlite3."""

    def __init__(self, url: str) -> None:
        import psycopg2
        import psycopg2.extras

        self._conn = psycopg2.connect(url)
        psycopg2.extras.register_default_jsonb(self._conn)
        self._dict_cursor_factory = psycopg2.extras.RealDictCursor

    def cursor(self) -> Any:
        return self._conn.cursor(cursor_factory=self._dict_cursor_factory)

    def execute(self, sql: str, params: tuple = ()) -> Any:
        cur = self._conn.cursor(cursor_factory=self._dict_cursor_factory)
        cur.execute(sql, params)
        return cur

    def executemany(self, sql: str, params_seq) -> Any:
        cur = self._conn.cursor(cursor_factory=self._dict_cursor_factory)
        cur.executemany(sql, params_seq)
        return cur

    def commit(self) -> None:
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            try:
                self._conn.rollback()
            except Exception:
                pass
        self.close()


class _Sqlite3Adapter:
    """Envuelve sqlite3.Connection con la misma interfaz."""

    def __init__(self, path: str) -> None:
        self._conn = sqlite3.connect(path)
        self._conn.row_factory = sqlite3.Row

    def cursor(self) -> Any:
        return self._conn.cursor()

    def execute(self, sql: str, params: tuple = ()) -> Any:
        return self._conn.execute(sql, params)

    def executemany(self, sql: str, params_seq) -> Any:
        return self._conn.executemany(sql, params_seq)

    def commit(self) -> None:
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def get_connection(local_path: str = "project_viability.db") -> _Sqlite3Adapter | _Psycopg2Adapter:
    if IS_CLOUD:
        return _Psycopg2Adapter(_DATABASE_URL)
    return _Sqlite3Adapter(local_path)


def db_table_exists(conn, table_name: str) -> bool:
    """Verifica si una tabla existe. Compatible con SQLite y PostgreSQL."""
    if IS_CLOUD:
        row = conn.execute(
            "SELECT table_name FROM information_schema.tables " "WHERE table_schema='public' AND table_name=%s LIMIT 1",
            (table_name,),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
            (table_name,),
        ).fetchone()
    return row is not None


def db_table_columns(conn, table_name: str) -> set[str]:
    """Retorna el set de nombres de columnas de una tabla. Compatible con SQLite y PostgreSQL."""
    if not db_table_exists(conn, table_name):
        return set()
    if IS_CLOUD:
        rows = conn.execute(
            "SELECT column_name FROM information_schema.columns " "WHERE table_schema='public' AND table_name=%s",
            (table_name,),
        ).fetchall()
        return {r["column_name"] for r in rows}
    else:
        rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        return {r["name"] for r in rows}


def db_now() -> str:
    """Retorna datetime UTC actual como string ISO para usar como parámetro SQL."""
    from datetime import datetime

    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
