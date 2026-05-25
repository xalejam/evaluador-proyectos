#!/usr/bin/env python3
"""Exporta datos de SQLite local a un archivo SQL para importar en Supabase.

Uso:
    python scripts/export_to_sql.py
Genera: scripts/migration_data.sql
"""

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SQLITE_PATH = ROOT / "project_viability.db"
OUTPUT = ROOT / "scripts" / "migration_data.sql"


def escape(val):
    if val is None:
        return "NULL"
    if isinstance(val, (int, float)):
        return str(val)
    s = str(val).replace("'", "''")
    return f"'{s}'"


def export_table(conn, table, columns, pk_conflict, out):
    rows = conn.execute(f"SELECT * FROM {table}").fetchall()
    if not rows:
        out.write(f"-- {table}: sin datos\n\n")
        return
    out.write(f"-- {table}: {len(rows)} filas\n")
    for r in rows:
        d = dict(r)
        cols = ", ".join(columns)
        vals = ", ".join(escape(d.get(c)) for c in columns)
        out.write(f"INSERT INTO {table} ({cols}) VALUES ({vals}) {pk_conflict};\n")
    out.write("\n")
    print(f"  {table}: {len(rows)} filas exportadas.")


def main():
    if not SQLITE_PATH.exists():
        print(f"ERROR: No se encontró {SQLITE_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(str(SQLITE_PATH))
    conn.row_factory = sqlite3.Row

    with OUTPUT.open("w", encoding="utf-8") as out:
        out.write("-- Migración SQLite → Supabase\n")
        out.write("-- Ejecutar en: Supabase > SQL Editor > New query\n\n")

        export_table(
            conn,
            "projects",
            [
                "id",
                "project_id",
                "name",
                "description",
                "created_date",
                "status",
                "last_tracking_update",
                "country",
                "owner",
                "current_time_per_task",
                "tasks_per_month",
                "staff_count",
                "avg_salary_per_hour",
                "time_reduction_percent",
                "development_hours",
                "development_cost_per_hour",
                "maintenance_monthly",
                "implementation_complexity",
                "risk_level",
                "viability_score",
                "priority",
                "monthly_savings",
                "annual_savings",
                "payback_period_months",
                "roi_first_year",
                "recommendation",
                "initial_development_cost",
                "hours_saved_per_month",
                "actual_monthly_savings",
                "actual_annual_savings",
                "loop_url",
                "repo_url",
                "artifacts_url",
                "artifacts_type",
                "tech_stack",
                "delivery_team",
                "updated_at",
                "closed_at",
            ],
            "ON CONFLICT (id) DO NOTHING",
            out,
        )

        export_table(
            conn,
            "project_notes",
            [
                "note_id",
                "project_id",
                "note_text",
                "note_type",
                "author",
                "tags",
                "is_private",
                "created_at",
                "entry_group_id",
                "note_title",
                "progress_percent",
                "estimated_end_date",
                "effort_hours",
            ],
            "ON CONFLICT (note_id) DO NOTHING",
            out,
        )

        export_table(
            conn,
            "project_evaluations",
            [
                "evaluation_id",
                "project_id",
                "created_at",
                "created_by",
                "action",
                "status_after",
                "score_total",
                "score_impact",
                "score_risk",
                "score_complexity",
                "monthly_savings",
                "annual_savings",
                "payback_period_months",
                "roi_first_year",
                "hours_saved_per_month",
                "inputs_json",
                "answers_json",
                "weights_json",
                "impact_score",
                "effort_score",
                "is_current",
            ],
            "ON CONFLICT (evaluation_id) DO NOTHING",
            out,
        )

        export_table(
            conn,
            "project_members",
            ["project_id", "member_name", "added_at"],
            "ON CONFLICT (project_id, member_name) DO NOTHING",
            out,
        )

    conn.close()
    print(f"\n✅ Archivo generado: {OUTPUT}")
    print("Abre Supabase > SQL Editor > New query y pega el contenido.")


if __name__ == "__main__":
    main()
