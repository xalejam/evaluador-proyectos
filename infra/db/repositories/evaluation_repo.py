"""Repositorio de snapshots de evaluaciones."""

from __future__ import annotations

import json
from typing import Any

from infra.db.connection import get_sqlite_conn


class EvaluationRepository:
    def __init__(self, db_path: str = "project_viability.db") -> None:
        self.db_path = db_path

    def insert_snapshot(
        self,
        project_id: str,
        action: str,
        status_after: str,
        calc_results: dict[str, Any],
        inputs_json: dict[str, Any],
        created_by: str,
    ) -> int:
        with get_sqlite_conn(self.db_path) as conn:
            cur = conn.execute(
                """
                INSERT INTO project_evaluations (
                    project_id, created_by, action, status_after,
                    score_total, score_impact, score_risk, score_complexity,
                    monthly_savings, annual_savings, payback_period_months, roi_first_year,
                    hours_saved_per_month, inputs_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    (created_by or "").strip(),
                    action,
                    status_after,
                    float(calc_results.get("viability_score", 0) or 0),
                    float(calc_results.get("score_impact", 0) or 0),
                    float(calc_results.get("score_risk", 0) or 0),
                    float(calc_results.get("score_complexity", 0) or 0),
                    float(calc_results.get("monthly_savings", 0) or 0),
                    float(calc_results.get("annual_savings", 0) or 0),
                    float(calc_results.get("payback_period_months", 0) or 0),
                    float(calc_results.get("roi_first_year", 0) or 0),
                    float(calc_results.get("hours_saved_per_month", 0) or 0),
                    json.dumps(inputs_json, ensure_ascii=False),
                ),
            )
            conn.commit()
            return int(cur.lastrowid)

    def list_snapshots(self, project_id: str) -> list[dict[str, Any]]:
        with get_sqlite_conn(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM project_evaluations
                WHERE project_id = ?
                ORDER BY datetime(created_at) DESC, evaluation_id DESC
                """,
                (project_id,),
            ).fetchall()
            return [dict(r) for r in rows]
