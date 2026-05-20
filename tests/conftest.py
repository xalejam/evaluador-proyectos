import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from infra.db.migrations import ensure_schema


@pytest.fixture
def temp_db_path(tmp_path: Path) -> Path:
    from infra.db_migrations import ensure_all_operational_schema
    db_path = tmp_path / "test_project_viability.db"
    conn = sqlite3.connect(db_path)
    ensure_all_operational_schema(conn)
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def temp_db_conn(temp_db_path: Path):
    conn = sqlite3.connect(temp_db_path)
    conn.row_factory = sqlite3.Row
    ensure_schema(conn)
    yield conn
    conn.close()
