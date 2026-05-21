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

    def cursor(self) -> Any:
        return self._conn.cursor()

    def execute(self, sql: str, params: tuple = ()) -> Any:
        cur = self._conn.cursor()
        cur.execute(sql, params)
        return cur

    def executemany(self, sql: str, params_seq) -> Any:
        cur = self._conn.cursor()
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
