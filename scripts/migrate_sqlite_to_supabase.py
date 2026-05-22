#!/usr/bin/env python3
"""Migra datos de SQLite local a Supabase (PostgreSQL).

Uso:
    $env:DATABASE_URL = "postgresql://..."
    python scripts/migrate_sqlite_to_supabase.py
"""

import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DATABASE_URL = os.environ.get("DATABASE_URL", "")
if not DATABASE_URL:
    print("ERROR: Define DATABASE_URL antes de ejecutar.")
    sys.exit(1)

import psycopg2
import psycopg2.extras

SQLITE_PATH = ROOT / "project_viability.db"
if not SQLITE_PATH.exists():
    print(f"ERROR: No se encontró {SQLITE_PATH}")
    sys.exit(1)


def get_sqlite():
    conn = sqlite3.connect(str(SQLITE_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def get_pg():
    conn = psycopg2.connect(DATABASE_URL)
    psycopg2.extras.register_default_jsonb(conn)
    return conn


def migrate_projects(sqlite_conn, pg_cur):
    rows = sqlite_conn.execute("SELECT * FROM projects").fetchall()
    print(f"  Migrando {len(rows)} proyectos...")
    for r in rows:
        pg_cur.execute("""
            INSERT INTO projects (
                id, project_id, name, description, created_date, status,
                last_tracking_update, country, owner,
                current_time_per_task, tasks_per_month, staff_count,
                avg_salary_per_hour, time_reduction_percent,
                development_hours, development_cost_per_hour, maintenance_monthly,
                implementation_complexity, risk_level, viability_score, priority,
                monthly_savings, annual_savings, payback_period_months, roi_first_year,
                recommendation, initial_development_cost, hours_saved_per_month,
                actual_monthly_savings, actual_annual_savings,
                loop_url, repo_url, artifacts_url, artifacts_type,
                tech_stack, delivery_team, updated_at, closed_at
            ) VALUES (
                %(id)s, %(project_id)s, %(name)s, %(description)s, %(created_date)s, %(status)s,
                %(last_tracking_update)s, %(country)s, %(owner)s,
                %(current_time_per_task)s, %(tasks_per_month)s, %(staff_count)s,
                %(avg_salary_per_hour)s, %(time_reduction_percent)s,
                %(development_hours)s, %(development_cost_per_hour)s, %(maintenance_monthly)s,
                %(implementation_complexity)s, %(risk_level)s, %(viability_score)s, %(priority)s,
                %(monthly_savings)s, %(annual_savings)s, %(payback_period_months)s, %(roi_first_year)s,
                %(recommendation)s, %(initial_development_cost)s, %(hours_saved_per_month)s,
                %(actual_monthly_savings)s, %(actual_annual_savings)s,
                %(loop_url)s, %(repo_url)s, %(artifacts_url)s, %(artifacts_type)s,
                %(tech_stack)s, %(delivery_team)s, %(updated_at)s, %(closed_at)s
            )
            ON CONFLICT (id) DO NOTHING
        """, dict(r))
    print(f"  OK: {len(rows)} proyectos.")


def migrate_notes(sqlite_conn, pg_cur):
    rows = sqlite_conn.execute("SELECT * FROM project_notes").fetchall()
    print(f"  Migrando {len(rows)} notas...")
    for r in rows:
        pg_cur.execute("""
            INSERT INTO project_notes (
                note_id, project_id, note_text, note_type, author, tags,
                is_private, created_at, entry_group_id, note_title,
                progress_percent, estimated_end_date, effort_hours
            ) VALUES (
                %(note_id)s, %(project_id)s, %(note_text)s, %(note_type)s, %(author)s, %(tags)s,
                %(is_private)s, %(created_at)s, %(entry_group_id)s, %(note_title)s,
                %(progress_percent)s, %(estimated_end_date)s, %(effort_hours)s
            )
            ON CONFLICT (note_id) DO NOTHING
        """, dict(r))
    print(f"  OK: {len(rows)} notas.")


def migrate_evaluations(sqlite_conn, pg_cur):
    rows = sqlite_conn.execute("SELECT * FROM project_evaluations").fetchall()
    print(f"  Migrando {len(rows)} evaluaciones...")
    for r in rows:
        pg_cur.execute("""
            INSERT INTO project_evaluations (
                evaluation_id, project_id, created_at, created_by, action,
                status_after, score_total, score_impact, score_risk, score_complexity,
                monthly_savings, annual_savings, payback_period_months, roi_first_year,
                hours_saved_per_month, inputs_json, answers_json, weights_json,
                impact_score, effort_score, is_current
            ) VALUES (
                %(evaluation_id)s, %(project_id)s, %(created_at)s, %(created_by)s, %(action)s,
                %(status_after)s, %(score_total)s, %(score_impact)s, %(score_risk)s, %(score_complexity)s,
                %(monthly_savings)s, %(annual_savings)s, %(payback_period_months)s, %(roi_first_year)s,
                %(hours_saved_per_month)s, %(inputs_json)s, %(answers_json)s, %(weights_json)s,
                %(impact_score)s, %(effort_score)s, %(is_current)s
            )
            ON CONFLICT (evaluation_id) DO NOTHING
        """, dict(r))
    print(f"  OK: {len(rows)} evaluaciones.")


def migrate_members(sqlite_conn, pg_cur):
    rows = sqlite_conn.execute("SELECT * FROM project_members").fetchall()
    print(f"  Migrando {len(rows)} miembros...")
    for r in rows:
        pg_cur.execute("""
            INSERT INTO project_members (project_id, member_name, added_at)
            VALUES (%(project_id)s, %(member_name)s, %(added_at)s)
            ON CONFLICT (project_id, member_name) DO NOTHING
        """, dict(r))
    print(f"  OK: {len(rows)} miembros.")


def main():
    print(f"Conectando a SQLite: {SQLITE_PATH}")
    sqlite_conn = get_sqlite()

    print("Conectando a Supabase...")
    pg_conn = get_pg()
    pg_cur = pg_conn.cursor()

    try:
        migrate_projects(sqlite_conn, pg_cur)
        migrate_notes(sqlite_conn, pg_cur)
        migrate_evaluations(sqlite_conn, pg_cur)
        migrate_members(sqlite_conn, pg_cur)
        pg_conn.commit()
        print("\n✅ Migración completada exitosamente.")
    except Exception as e:
        pg_conn.rollback()
        print(f"\n❌ Error durante migración: {e}")
        raise
    finally:
        sqlite_conn.close()
        pg_cur.close()
        pg_conn.close()


if __name__ == "__main__":
    main()
