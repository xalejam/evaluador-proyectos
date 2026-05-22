import os
import sqlite3
import tempfile

from infra.db.migrations import ensure_evaluations_schema, ensure_projects_schema


def test_consolidated_schema_has_matrix_columns():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    conn = sqlite3.connect(db_path)
    try:
        ensure_projects_schema(conn)
        ensure_evaluations_schema(conn)
        cursor = conn.execute("PRAGMA table_info(project_evaluations)")
        columns = {row[1] for row in cursor}
        assert "impact_score" in columns
        assert "effort_score" in columns
        assert "answers_json" in columns
        assert "weights_json" in columns
        assert "is_current" in columns
    finally:
        conn.close()
        os.unlink(db_path)
