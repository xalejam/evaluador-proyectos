import json

from domain.services.executive_summary_service import (
    compute_portfolio_summary,
    format_fte_equivalent,
    load_project_notes,
    resolve_project_note,
)


def test_fte_under_8_weeks_shows_weeks_and_hours():
    assert format_fte_equivalent(100) == "2 semanas y 20 h"


def test_fte_exact_weeks_omits_hours():
    assert format_fte_equivalent(40) == "1 semana"


def test_fte_plural_weeks():
    assert format_fte_equivalent(80) == "2 semanas"


def test_fte_between_8_and_52_weeks_shows_months():
    assert format_fte_equivalent(2000) == "11.5 meses"


def test_fte_52_weeks_or_more_shows_years_and_months():
    assert format_fte_equivalent(5661.54) == "2 años y 9 meses"


def test_fte_exact_years_omits_months():
    assert format_fte_equivalent(40 * 52 * 3) == "3 años"


def test_fte_singular_year():
    assert format_fte_equivalent(40 * 52) == "1 año"


def _project(project_id, name, status, hours=0.0):
    return {"project_id": project_id, "name": name, "status": status, "hours_saved_per_month": hours}


def test_compute_portfolio_summary_counts_and_sums_closed_only():
    projects = [
        _project("A", "Proyecto A", "implemented", hours=100),
        _project("B", "Proyecto B", "handed_off", hours=5000),
        _project("C", "Proyecto C", "executing", hours=9999),  # no cuenta en el ahorro
        _project("D", "Proyecto D", "approved"),
    ]
    summary = compute_portfolio_summary(projects)
    assert summary.hours_saved_closed == 5100
    assert summary.closed_count == 2
    assert summary.executing_count == 1
    assert summary.fte_equivalent == format_fte_equivalent(5100)


def test_compute_portfolio_summary_top_contributor():
    projects = [
        _project("A", "Proyecto chico", "implemented", hours=10),
        _project("B", "Proyecto grande", "handed_off", hours=5000),
    ]
    summary = compute_portfolio_summary(projects)
    assert summary.top_contributor == "Proyecto grande (5,000 h/mes)"


def test_compute_portfolio_summary_status_counts_include_zeros():
    projects = [_project("A", "Proyecto A", "implemented", hours=10)]
    summary = compute_portfolio_summary(projects)
    assert summary.status_counts == {
        "evaluated": 0,
        "backlog": 0,
        "approved": 0,
        "executing": 0,
        "implemented": 1,
        "on_hold": 0,
        "handed_off": 0,
        "rejected": 0,
    }


def test_compute_portfolio_summary_no_closed_projects():
    projects = [_project("A", "Proyecto A", "executing", hours=10)]
    summary = compute_portfolio_summary(projects)
    assert summary.hours_saved_closed == 0
    assert summary.top_contributor == "N/D"
    assert summary.fte_equivalent == format_fte_equivalent(0)


def test_compute_portfolio_summary_ignores_unknown_status():
    # defensivo: un status fuera del enum no debe romper el conteo
    projects = [_project("A", "Proyecto A", "algo_nuevo", hours=10)]
    summary = compute_portfolio_summary(projects)
    assert summary.closed_count == 0
    assert summary.executing_count == 0


def test_load_project_notes_returns_empty_dict_when_path_is_none():
    assert load_project_notes(None) == {}


def test_load_project_notes_returns_empty_dict_when_file_missing(tmp_path):
    assert load_project_notes(str(tmp_path / "no-existe.json")) == {}


def test_load_project_notes_indexes_by_project_id(tmp_path):
    path = tmp_path / "notas.json"
    path.write_text(
        json.dumps(
            {
                "generated_at": "2026-09-04",
                "projects": [
                    {"project_id": "MX-DDD-0005", "que_es": "Automatiza Order Forms.", "estado_frase": "Implementado."},
                ],
            }
        ),
        encoding="utf-8",
    )
    notes = load_project_notes(str(path))
    assert notes["MX-DDD-0005"]["que_es"] == "Automatiza Order Forms."


def test_resolve_project_note_uses_notes_when_present():
    project = {"project_id": "MX-DDD-0005", "name": "Order Forms", "status": "implemented"}
    notes_by_id = {"MX-DDD-0005": {"que_es": "Automatiza Order Forms.", "estado_frase": "Implementado."}}
    que_es, estado_frase = resolve_project_note(project, notes_by_id)
    assert que_es == "Automatiza Order Forms."
    assert estado_frase == "Implementado."


def test_resolve_project_note_falls_back_when_missing():
    project = {"project_id": "XX-DDD-0099", "name": "Proyecto sin notas", "status": "approved"}
    que_es, estado_frase = resolve_project_note(project, {})
    assert que_es == "Proyecto sin notas — sin resumen disponible."
    assert estado_frase == "Estado: Aprobado."
