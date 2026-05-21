import csv
import io
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from infra.db_migrations import ensure_notes_schema


@pytest.fixture
def db_with_notes(tmp_path):
    db_file = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    ensure_notes_schema(conn)
    conn.execute(
        "INSERT INTO project_notes (note_id, project_id, note_text, note_type, author) VALUES (1,'P1','texto','general','Xiomara')"
    )
    conn.execute(
        "INSERT INTO project_notes (note_id, project_id, note_text, note_type, author) VALUES (2,'P1','texto2','proximo_paso','Xiomara')"
    )
    conn.commit()
    conn.close()
    return db_file


def _run_import(db_path, rows):
    """Helper: escribe CSV temporal y llama a la logica de importacion."""
    from scripts.import_notes_hours import import_hours

    buf = io.StringIO()
    writer = csv.DictWriter(
        buf, fieldnames=["note_id", "project_id", "note_type", "note_title", "created_at", "note_text", "effort_hours"]
    )
    writer.writeheader()
    for r in rows:
        writer.writerow(r)
    buf.seek(0)
    return import_hours(str(db_path), buf)


def test_valid_import_updates_hours(db_with_notes):
    result = _run_import(
        db_with_notes,
        [
            {
                "note_id": 1,
                "project_id": "P1",
                "note_type": "general",
                "note_title": "",
                "created_at": "",
                "note_text": "",
                "effort_hours": 4.5,
            },
            {
                "note_id": 2,
                "project_id": "P1",
                "note_type": "proximo_paso",
                "note_title": "",
                "created_at": "",
                "note_text": "",
                "effort_hours": 2.0,
            },
        ],
    )
    assert result["updated"] == 2
    assert result["rejected"] == 0

    conn = sqlite3.connect(str(db_with_notes))
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT effort_hours FROM project_notes WHERE note_id=1").fetchone()
    assert row["effort_hours"] == 4.5
    conn.close()


def test_zero_hours_rejected(db_with_notes):
    result = _run_import(
        db_with_notes,
        [
            {
                "note_id": 1,
                "project_id": "P1",
                "note_type": "general",
                "note_title": "",
                "created_at": "",
                "note_text": "",
                "effort_hours": 0,
            },
        ],
    )
    assert result["rejected"] == 1
    assert len(result["rejected_rows"]) == 1


def test_empty_hours_rejected(db_with_notes):
    result = _run_import(
        db_with_notes,
        [
            {
                "note_id": 1,
                "project_id": "P1",
                "note_type": "general",
                "note_title": "",
                "created_at": "",
                "note_text": "",
                "effort_hours": "",
            },
        ],
    )
    assert result["rejected"] == 1


def test_nonexistent_note_id_rejected(db_with_notes):
    result = _run_import(
        db_with_notes,
        [
            {
                "note_id": 999,
                "project_id": "P1",
                "note_type": "general",
                "note_title": "",
                "created_at": "",
                "note_text": "",
                "effort_hours": 3.0,
            },
        ],
    )
    assert result["rejected"] == 1


def test_negative_hours_rejected(db_with_notes):
    result = _run_import(
        db_with_notes,
        [
            {
                "note_id": 1,
                "project_id": "P1",
                "note_type": "general",
                "note_title": "",
                "created_at": "",
                "note_text": "",
                "effort_hours": -1.5,
            },
        ],
    )
    assert result["rejected"] == 1
