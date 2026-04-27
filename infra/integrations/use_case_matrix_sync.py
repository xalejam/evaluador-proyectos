"""Sincronización de scores Impact/Effort hacia project_viability.db.

Escribe directamente en project_evaluations (columnas is_current, impact_score,
effort_score, answers_json, weights_json) eliminando la dependencia de data/projects.db.
"""

from __future__ import annotations

import json

from domain.scoring import calculate_scores
from infra.config_loader import ConfigLoader
from infra.db.connection import get_sqlite_conn


def _clamp_score(value: int) -> int:
    return max(1, min(5, int(value)))


def _score_from_thresholds(value: float, thresholds: list[float]) -> int:
    if value <= thresholds[0]:
        return 1
    if value <= thresholds[1]:
        return 2
    if value <= thresholds[2]:
        return 3
    if value <= thresholds[3]:
        return 4
    return 5


def _derive_matrix_answers(project_data: dict, results: dict) -> dict[str, int]:
    staff = float(project_data.get("staff_count", 1) or 1)
    tasks = float(project_data.get("tasks_per_month", 0) or 0)
    reduction = float(project_data.get("time_reduction_percent", 0) or 0)
    dev_hours = float(project_data.get("development_hours", 0) or 0)
    complexity = int(project_data.get("implementation_complexity", 3) or 3)
    risk = int(project_data.get("risk_level", 3) or 3)
    annual_savings = float(results.get("annual_savings", 0) or 0)

    return {
        "A": _score_from_thresholds(reduction, [5, 15, 30, 50]),
        "B": _score_from_thresholds(staff, [1, 2, 4, 7]),
        "C": _score_from_thresholds(tasks, [5, 20, 50, 100]),
        "D": _score_from_thresholds(annual_savings, [1000, 5000, 20000, 100000]),
        "E": _clamp_score(complexity),
        "F": _score_from_thresholds(dev_hours, [20, 80, 160, 320]),
        "G": _clamp_score(risk),
        "H": _score_from_thresholds(staff, [2, 5, 10, 20]),
    }


def sync_to_use_case_matrix(
    project_id: str,
    project_payload: dict,
    calc_results: dict,
    db_path: str = "project_viability.db",
) -> None:
    cfg = ConfigLoader().load()
    default_weights = cfg.get("default_weights", {k: 1.0 for k in "ABCDEFGH"})
    weights = {k: float(default_weights.get(k, 1.0)) for k in "ABCDEFGH"}
    answers = _derive_matrix_answers(project_payload, calc_results)
    impact_score, effort_score = calculate_scores(answers, weights)

    with get_sqlite_conn(db_path) as conn:
        conn.execute(
            "UPDATE project_evaluations SET is_current = 0 WHERE project_id = ? AND is_current = 1",
            (project_id,),
        )
        conn.execute(
            """
            INSERT INTO project_evaluations
                (project_id, action, status_after, score_total, inputs_json,
                 answers_json, weights_json, impact_score, effort_score, is_current)
            VALUES (?, 'matrix_sync', NULL, NULL, NULL, ?, ?, ?, ?, 1)
            """,
            (
                project_id,
                json.dumps(answers),
                json.dumps(weights),
                float(impact_score),
                float(effort_score),
            ),
        )
        conn.commit()


# Public aliases for import from other modules
derive_matrix_answers = _derive_matrix_answers
score_from_thresholds = _score_from_thresholds
clamp_score = _clamp_score
