import sqlite3
import tempfile

from domain.services.seguimiento_operativo_service import OperationalTrackingService


def _service() -> OperationalTrackingService:
    tmp = tempfile.mktemp(suffix=".db")
    svc = OperationalTrackingService(tmp)
    svc.ensure_schema()
    return svc


def _last_effort_hours(db_path: str, note_type: str):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT effort_hours FROM project_notes WHERE note_type = ? ORDER BY note_id DESC LIMIT 1",
        (note_type,),
    ).fetchone()
    conn.close()
    return row["effort_hours"] if row else None


def test_add_update_persists_effort_hours_on_general_note():
    svc = _service()
    svc.add_update(
        "P1",
        {"general": "Avance semanal", "proximo_paso": "", "bloqueador": "", "riesgo": ""},
        "Xiomara",
        "",
        effort_hours=6.5,
    )
    assert _last_effort_hours(svc.db_path, "general") == 6.5


def test_add_update_does_not_attach_effort_hours_to_other_note_types():
    svc = _service()
    svc.add_update(
        "P1",
        {"general": "Avance", "proximo_paso": "Siguiente paso", "bloqueador": "", "riesgo": ""},
        "Xiomara",
        "",
        effort_hours=3.0,
    )
    assert _last_effort_hours(svc.db_path, "proximo_paso") is None


def test_add_update_effort_hours_defaults_to_none():
    svc = _service()
    svc.add_update(
        "P1",
        {"general": "Avance sin horas", "proximo_paso": "", "bloqueador": "", "riesgo": ""},
        "Xiomara",
        "",
    )
    assert _last_effort_hours(svc.db_path, "general") is None
