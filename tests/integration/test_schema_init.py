import os
import sqlite3
import tempfile

from infra.db_migrations import ensure_all_operational_schema


def test_ensure_all_operational_schema_creates_project_notes():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        conn = sqlite3.connect(db_path)
        ensure_all_operational_schema(conn)
        conn.commit()
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='project_notes'")
        assert cursor.fetchone() is not None, "project_notes table should exist after ensure_all_operational_schema"
        conn.close()
    finally:
        os.unlink(db_path)
