from infra.db.repositories.evaluation_repo import EvaluationRepository
from infra.db.repositories.notes_repo import NotesRepository
from infra.db.repositories.project_repo import ProjectRepository


def _seed_project(repo: ProjectRepository, project_id: str = "MX-TEST-0001"):
    repo.upsert_project(
        {
            "id": project_id,
            "project_id": project_id,
            "name": "Proyecto Test",
            "owner": "TEST",
            "country": "MX",
            "status": "evaluated",
        }
    )


def test_notes_repo_insert_and_latest(temp_db_path):
    project_repo = ProjectRepository(str(temp_db_path))
    notes_repo = NotesRepository(str(temp_db_path))
    _seed_project(project_repo)

    notes_repo.insert_notes_batch(
        [
            {
                "project_id": "MX-TEST-0001",
                "note_type": "general",
                "note_text": "Inicio de proyecto",
                "author": "tester",
                "entry_group_id": "grp1",
            },
            {
                "project_id": "MX-TEST-0001",
                "note_type": "riesgo",
                "note_text": "Riesgo de capacidad",
                "author": "tester",
                "entry_group_id": "grp1",
            },
        ]
    )

    latest = notes_repo.get_latest_notes_by_type("MX-TEST-0001")
    assert "general" in latest
    assert latest["general"]["note_text"] == "Inicio de proyecto"
    assert latest["riesgo"]["note_text"] == "Riesgo de capacidad"


def test_evaluation_repo_insert_and_list(temp_db_path):
    project_repo = ProjectRepository(str(temp_db_path))
    eval_repo = EvaluationRepository(str(temp_db_path))
    _seed_project(project_repo)

    eval_id = eval_repo.insert_snapshot(
        project_id="MX-TEST-0001",
        action="evaluation_saved",
        status_after="evaluated",
        calc_results={"viability_score": 80, "monthly_savings": 1000, "annual_savings": 12000},
        inputs_json={"name": "Proyecto Test"},
        created_by="tester",
    )
    assert eval_id > 0

    rows = eval_repo.list_snapshots("MX-TEST-0001")
    assert len(rows) >= 1
    assert rows[0]["project_id"] == "MX-TEST-0001"
    assert rows[0]["action"] == "evaluation_saved"
