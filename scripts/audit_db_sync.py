"""Audits divergence between project_viability.db and data/projects.db."""
import sqlite3
import sys

DB_MAIN = "project_viability.db"
DB_MATRIX = "data/projects.db"


def audit():
    conn_main = sqlite3.connect(DB_MAIN)
    conn_matrix = sqlite3.connect(DB_MATRIX)

    main_rows = {
        row[0]: row
        for row in conn_main.execute(
            "SELECT project_id, country, owner, name, status, delivery_team, loop_url, updated_at "
            "FROM projects"
        )
    }
    matrix_ids = {
        row[0]
        for row in conn_matrix.execute("SELECT project_id FROM projects")
    }

    missing = set(main_rows.keys()) - matrix_ids
    print(f"Projects missing from matrix DB: {len(missing)}")
    for pid in missing:
        print(f"  MISSING: {pid}")

    conn_main.close()
    conn_matrix.close()
    return missing


if __name__ == "__main__":
    missing = audit()
    if missing:
        sys.exit(1)
