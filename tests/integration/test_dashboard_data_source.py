import sqlite3
import tempfile
from infra.db_migrations import ensure_all_operational_schema
from infra.db.repositories.project_repo import ProjectRepository


def test_dashboard_projects_come_from_sqlite(tmp_path):
    db_path = str(tmp_path / "test.db")
    conn = sqlite3.connect(db_path)
    ensure_all_operational_schema(conn)
    conn.commit()
    conn.close()

    repo = ProjectRepository(db_path)
    repo.upsert_project(
        {
            "id": "MX-TEST-0001",
            "project_id": "MX-TEST-0001",
            "country": "MX",
            "owner": "TEST",
            "name": "Proyecto de prueba",
            "status": "executing",
            "viability_score": 85.0,
            "monthly_savings": 1000.0,
            "annual_savings": 12000.0,
        }
    )

    projects = repo.list_projects()
    assert len(projects) == 1
    assert projects[0]["project_id"] == "MX-TEST-0001"
    assert projects[0]["viability_score"] == 85.0
