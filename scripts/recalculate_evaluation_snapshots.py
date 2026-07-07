"""Recalcula snapshots de project_evaluations con la formula financiera corregida.

Los datos reales viven en Supabase (PostgreSQL); el destino se selecciona via
DATABASE_URL en infra/db/adapter.py. Sin DATABASE_URL corre contra SQLite local.

Uso:
    python scripts/recalculate_evaluation_snapshots.py --dry-run --verbose
    python scripts/recalculate_evaluation_snapshots.py --apply --verbose
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from domain.scoring.financials import compute_financials  # noqa: E402
from infra.db.adapter import IS_CLOUD, PLACEHOLDER, get_connection  # noqa: E402

_FINANCIAL_KEYS = (
    "current_time_per_task",
    "tasks_per_month",
    "staff_count",
    "avg_salary_per_hour",
    "time_reduction_percent",
    "development_hours",
    "development_cost_per_hour",
    "maintenance_monthly",
)


def parse_inputs_json(raw: str | dict | None) -> dict[str, Any]:
    """Normaliza inputs_json a dict. En SQLite viene como str; en PG como dict (jsonb)."""
    if raw is None:
        return {}
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except (ValueError, TypeError):
            return {}
    if isinstance(raw, dict):
        return raw
    return {}


def _engine_label() -> str:
    return "Supabase (PostgreSQL, IS_CLOUD=True)" if IS_CLOUD else "SQLite local (IS_CLOUD=False)"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Recalcula snapshots financieros.")
    parser.add_argument("--dry-run", action="store_true", help="No escribe; solo reporta diferencias.")
    parser.add_argument("--apply", action="store_true", help="Aplica cambios a la base de datos.")
    parser.add_argument("--verbose", action="store_true", help="Detalla cada cambio.")
    args = parser.parse_args(argv)

    if not args.dry_run and not args.apply:
        # Sin flags: modo dry-run por defecto para evitar escrituras accidentales
        args.dry_run = True
        print("AVISO: Ningún flag especificado. Ejecutando en modo --dry-run por seguridad.")
        print("       Usa --apply para escribir cambios a la base de datos.")

    print(f"Motor: {_engine_label()}")
    if args.dry_run:
        print("Modo: DRY-RUN (no se escribira nada)")
    elif args.apply:
        print("Modo: APPLY (se escribiran cambios a la base de datos)")

    with get_connection() as conn:
        rows = conn.execute(
            "SELECT evaluation_id, project_id, monthly_savings, annual_savings, "
            "payback_period_months, roi_first_year, hours_saved_per_month, inputs_json "
            "FROM project_evaluations"
        ).fetchall()
        rows = [dict(r) for r in rows]

    updated = unchanged = skipped = errors = 0
    pending: list[tuple] = []  # (hours, monthly, annual, payback, roi, evaluation_id)

    for row in rows:
        inputs = parse_inputs_json(row.get("inputs_json"))
        if not all(k in inputs for k in _FINANCIAL_KEYS):
            skipped += 1
            if args.verbose:
                print(f"  OMITIDO evaluation_id={row['evaluation_id']} | inputs_json incompleto")
            continue

        try:
            calc = compute_financials(
                current_time_per_task=float(inputs["current_time_per_task"]),
                tasks_per_month=int(inputs["tasks_per_month"]),
                staff_count=int(inputs["staff_count"]),
                avg_salary_per_hour=float(inputs["avg_salary_per_hour"]),
                time_reduction_percent=float(inputs["time_reduction_percent"]),
                development_hours=float(inputs["development_hours"]),
                development_cost_per_hour=float(inputs["development_cost_per_hour"]),
                maintenance_monthly=float(inputs["maintenance_monthly"]),
            )
        except (ValueError, TypeError, KeyError) as exc:
            errors += 1
            print(f"  ERROR evaluation_id={row['evaluation_id']}: {exc}")
            continue

        new_hours = calc["hours_saved_per_month"]
        old_hours = row.get("hours_saved_per_month")
        if old_hours is not None and abs(float(old_hours) - new_hours) < 1e-6:
            unchanged += 1
            continue

        updated += 1
        pending.append(
            (
                calc["hours_saved_per_month"],
                calc["monthly_savings"],
                calc["annual_savings"],
                calc["payback_period_months"],
                calc["roi_first_year"],
                row["evaluation_id"],
            )
        )
        if args.verbose:
            print(
                f"  evaluation_id={row['evaluation_id']} | project_id={row['project_id']}\n"
                f"    hours_saved_per_month: {old_hours} -> {new_hours:.4f}\n"
                f"    monthly_savings:       {row.get('monthly_savings')} -> {calc['monthly_savings']:.2f}\n"
                f"    annual_savings:        {row.get('annual_savings')} -> {calc['annual_savings']:.2f}\n"
                f"    roi_first_year:        {row.get('roi_first_year')} -> {calc['roi_first_year']:.2f}"
            )

    if pending and args.apply and not args.dry_run:
        with get_connection() as conn:
            for params in pending:
                conn.execute(
                    "UPDATE project_evaluations SET "
                    "hours_saved_per_month = " + PLACEHOLDER + ", "
                    "monthly_savings = " + PLACEHOLDER + ", "
                    "annual_savings = " + PLACEHOLDER + ", "
                    "payback_period_months = " + PLACEHOLDER + ", "
                    "roi_first_year = " + PLACEHOLDER + " "
                    "WHERE evaluation_id = " + PLACEHOLDER,
                    params,
                )
            conn.commit()
        print(f"\nCommit realizado: {len(pending)} filas actualizadas.")

    print(f"\nSnapshots procesados: {len(rows)}")
    print(f"  Actualizados: {updated}")
    print(f"  Sin cambios:  {unchanged}")
    print(f"  Omitidos:     {skipped} (inputs_json incompleto)")
    print(f"  Errores:      {errors}")
    if args.dry_run and pending:
        print(f"\n  (DRY-RUN: {len(pending)} filas se actualizarian en una corrida real con --apply)")

    # Validacion especifica HI-DDD-0002: verificar que el calculo sea correcto
    _validate_hi_ddd_0002(args.verbose)

    return 0


def _validate_hi_ddd_0002(verbose: bool = False) -> None:
    """Valida que la formula corregida produce exactamente 4.08 h/mes para HI-DDD-0002."""
    result = compute_financials(
        current_time_per_task=0.08,
        tasks_per_month=60,
        staff_count=1,
        avg_salary_per_hour=100,
        time_reduction_percent=85,
        development_hours=100,
        development_cost_per_hour=100,
        maintenance_monthly=0,
    )
    expected = 4.08
    actual = result["hours_saved_per_month"]
    ok = abs(actual - expected) < 1e-6
    status = "OK" if ok else "FALLO"
    print(f"\nValidacion HI-DDD-0002: hours_saved_per_month = {actual:.4f} (esperado {expected}) [{status}]")
    if not ok:
        print("  ADVERTENCIA: La formula no produce el valor esperado.")


if __name__ == "__main__":
    sys.exit(main())
