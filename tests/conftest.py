import sqlite3
from pathlib import Path

import pytest

from infra.db.migrations import ensure_schema


@pytest.fixture
def temp_db_path(tmp_path: Path) -> Path:
    return tmp_path / "test_project_viability.db"


@pytest.fixture
def temp_db_conn(temp_db_path: Path):
    conn = sqlite3.connect(temp_db_path)
    conn.row_factory = sqlite3.Row
    ensure_schema(conn)
    yield conn
    conn.close()
