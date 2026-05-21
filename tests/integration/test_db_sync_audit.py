import sqlite3
import os
import pytest

DB_MAIN = os.path.abspath("project_viability.db")
DB_MATRIX = os.path.abspath("data/projects.db")


@pytest.mark.skipif(
    not os.path.exists(DB_MAIN) or not os.path.exists(DB_MATRIX), reason="DBs not present in this environment"
)
def test_no_approved_projects_missing_from_matrix():
    conn_main = sqlite3.connect(DB_MAIN)
    conn_matrix = sqlite3.connect(DB_MATRIX)

    main_ids = {
        row[0]
        for row in conn_main.execute(
            "SELECT project_id FROM projects WHERE status IN ('approved','executing','implemented')"
        )
    }
    matrix_ids = {row[0] for row in conn_matrix.execute("SELECT project_id FROM projects")}

    conn_main.close()
    conn_matrix.close()

    missing = main_ids - matrix_ids
    assert not missing, f"Projects in main DB not synced to matrix DB: {missing}"
