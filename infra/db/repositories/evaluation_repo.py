"""Repositorio de snapshots de evaluaciones."""

from __future__ import annotations

import json
from typing import Any

from infra.db.adapter import IS_CLOUD, PLACEHOLDER
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
        placeholders = ", ".join([PLACEHOLDER] * 14)
        with get_sqlite_conn(self.db_path) as conn:
            conn.execute(
                f"""
                INSERT INTO project_evaluations (
                    project_id, created_by, action, status_after,
                    score_total, score_impact, score_risk, score_complexity,
                    monthly_savings, annual_savings, payback_period_months, roi_first_year,
                    hours_saved_per_month, inputs_json
                ) VALUES ({placeholders})
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
                    calc_results.get("payback_period_months"),
                    float(calc_results.get("roi_first_year", 0) or 0),
                    float(calc_results.get("hours_saved_per_month", 0) or 0),
                    json.dumps(inputs_json, ensure_ascii=False),
                ),
            )
            if IS_CLOUD:
                row = conn.execute("SELECT MAX(evaluation_id) AS last_id FROM project_evaluations").fetchone()
            else:
                row = conn.execute("SELECT last_insert_rowid() AS last_id").fetchone()
            conn.commit()
            return int(row["last_id"] or 0) if row else 0

    def list_snapshots(self, project_id: str) -> list[dict[str, Any]]:
        order_expr = "created_at" if IS_CLOUD else "datetime(created_at)"
        with get_sqlite_conn(self.db_path) as conn:
            rows = conn.execute(
                f"""
                SELECT *
                FROM project_evaluations
                WHERE project_id = {PLACEHOLDER}
                ORDER BY {order_expr} DESC, evaluation_id DESC
                """,
                (project_id,),
            ).fetchall()
            return [dict(r) for r in rows]
