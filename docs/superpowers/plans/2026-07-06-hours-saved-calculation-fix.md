# Hours Saved Calculation Fix — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Corregir la fórmula de `hours_saved_per_month` (quitar el factor `staff_count`), blindarla con tests parametrizados, y recalcular los snapshots históricos ya guardados en Supabase.

**Architecture:** Un cambio de una línea en la función pura `compute_financials()` corrige la fórmula y, por cascada, los 4 campos financieros derivados. Los tests demuestran independencia de `staff_count`. Un script standalone recorre `project_evaluations`, re-ejecuta `compute_financials()` sobre el `inputs_json` guardado de cada snapshot, y reescribe las filas cambiadas usando el adaptador `infra/db/adapter.py` (compatible SQLite/Supabase).

**Tech Stack:** Python 3, pytest, SQLite (local) / PostgreSQL vía psycopg2 (Supabase), `infra/db/adapter.py`.

## Global Constraints

- El script de recalculate DEBE usar `get_connection()`, `IS_CLOUD` y `PLACEHOLDER` de `infra/db/adapter.py`. Prohibido conectar directamente o asumir SQLite.
- El destino real es **Supabase (PostgreSQL)**; se selecciona vía variable de entorno `DATABASE_URL`. SQLite local solo se usa para pruebas del script.
- `inputs_json` puede venir como `str` (SQLite TEXT) o como `dict` (PostgreSQL jsonb). Siempre verificar `isinstance(raw, str)` antes de `json.loads()`.
- La firma de `compute_financials()` NO cambia (mantener compatibilidad con todos los llamadores).
- `--dry-run` nunca debe hacer `commit()`. La corrida real hace un único `commit()` al final.
- Llaves exactas en `inputs_json` (verificadas en `ui/tabs/planning.py`): `current_time_per_task`, `tasks_per_month`, `staff_count`, `avg_salary_per_hour`, `time_reduction_percent`, `development_hours`, `development_cost_per_hour`, `maintenance_monthly`.

---

## File Structure

| Archivo | Responsabilidad |
|---|---|
| `domain/scoring/financials.py` | Fórmula corregida (quitar `* staff_count` en línea 17) |
| `tests/unit/test_financials.py` | Tests parametrizados que prueban independencia de `staff_count` |
| `scripts/recalculate_evaluation_snapshots.py` | Recorrer snapshots, recalcular, reescribir filas cambiadas en Supabase |

---

## Task 1: Corregir la fórmula y blindarla con tests

**Files:**
- Modify: `domain/scoring/financials.py:17`
- Test: `tests/unit/test_financials.py`

**Interfaces:**
- Consumes: `compute_financials(current_time_per_task, tasks_per_month, staff_count, avg_salary_per_hour, time_reduction_percent, development_hours, development_cost_per_hour, maintenance_monthly) -> dict[str, float]` (firma existente, sin cambios).
- Produces: `compute_financials` con `hours_saved_per_month = time_saved * tasks_per_month` (sin `staff_count`). Consumido por Task 3.

- [ ] **Step 1: Escribir el test que falla (independencia de staff_count)**

Agregar al final de `tests/unit/test_financials.py`. Nota: el archivo actual NO importa `pytest`; agregar el import al inicio si no existe.

```python
import pytest

from domain.scoring.financials import compute_financials


@pytest.mark.parametrize("staff_count", [1, 5, 200])
def test_hours_saved_per_month_independent_of_staff_count(staff_count):
    """hours_saved_per_month no debe depender de staff_count.

    tasks_per_month ya representa el volumen total del proceso/equipo.
    Caso base HI-DDD-0002: 0.08h x 60 tareas x 85% = 4.08 h/mes.
    """
    result = compute_financials(
        current_time_per_task=0.08,
        tasks_per_month=60,
        staff_count=staff_count,
        avg_salary_per_hour=100,
        time_reduction_percent=85,
        development_hours=100,
        development_cost_per_hour=100,
        maintenance_monthly=0,
    )
    assert result["hours_saved_per_month"] == pytest.approx(4.08, rel=1e-6)


def test_hours_saved_hi_ddd_0002_regression():
    """Regresion explicita HI-DDD-0002: el valor correcto es 4.08, no 8.16."""
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
    assert result["hours_saved_per_month"] == pytest.approx(4.08, rel=1e-6)
    assert result["monthly_savings"] == pytest.approx(408.0, rel=1e-6)
    assert result["annual_savings"] == pytest.approx(4896.0, rel=1e-6)
```

- [ ] **Step 2: Correr el test para verificar que falla**

Run: `pytest tests/unit/test_financials.py::test_hours_saved_per_month_independent_of_staff_count -v`
Expected: FAIL — el caso `staff_count=5` da 20.4 y `staff_count=200` da 816.0 (por el `* staff_count` actual), no 4.08.

- [ ] **Step 3: Aplicar el fix mínimo en la fórmula**

En `domain/scoring/financials.py`, línea 17:

```python
# Antes:
    hours_saved_per_month = time_saved * tasks_per_month * staff_count
# Despues:
    hours_saved_per_month = time_saved * tasks_per_month
```

- [ ] **Step 4: Correr los tests para verificar que pasan**

Run: `pytest tests/unit/test_financials.py -v`
Expected: PASS — los 3 casos parametrizados + regresión HI-DDD-0002 + los 3 tests de payback existentes pasan.

- [ ] **Step 5: Commit**

```bash
git add domain/scoring/financials.py tests/unit/test_financials.py
git commit -m "fix: hours_saved_per_month no debe multiplicar por staff_count"
```

---

## Task 2: Esqueleto del script de recalculate (conexión + lectura + reporte)

**Files:**
- Create: `scripts/recalculate_evaluation_snapshots.py`

**Interfaces:**
- Consumes: `get_connection(local_path="project_viability.db")`, `IS_CLOUD`, `PLACEHOLDER` de `infra.db.adapter`; `compute_financials` de `domain.scoring.financials`.
- Produces: función `main(argv: list[str] | None = None) -> int` (CLI entrypoint); función `parse_inputs_json(raw: str | dict) -> dict` que normaliza el `inputs_json` a `dict`. Ambas consumidas/extendidas en Task 3.

- [ ] **Step 1: Crear el script con parsing de args, conexión y conteo de snapshots**

Crear `scripts/recalculate_evaluation_snapshots.py`:

```python
"""Recalcula snapshots de project_evaluations con la formula financiera corregida.

Los datos reales viven en Supabase (PostgreSQL); el destino se selecciona via
DATABASE_URL en infra/db/adapter.py. Sin DATABASE_URL corre contra SQLite local.

Uso:
    python scripts/recalculate_evaluation_snapshots.py --dry-run --verbose
    python scripts/recalculate_evaluation_snapshots.py
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from domain.scoring.financials import compute_financials
from infra.db.adapter import IS_CLOUD, PLACEHOLDER, get_connection

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
    parser.add_argument("--dry-run", action="store_true", help="No escribe; solo reporta.")
    parser.add_argument("--verbose", action="store_true", help="Detalla cada cambio.")
    args = parser.parse_args(argv)

    print(f"Motor: {_engine_label()}")
    if args.dry_run:
        print("Modo: DRY-RUN (no se escribira nada)")

    with get_connection() as conn:
        rows = conn.execute(
            "SELECT evaluation_id, project_id, monthly_savings, annual_savings, "
            "payback_period_months, roi_first_year, hours_saved_per_month, inputs_json "
            "FROM project_evaluations"
        ).fetchall()
        rows = [dict(r) for r in rows]

    print(f"Snapshots procesados: {len(rows)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Correr el script en dry-run contra SQLite local para verificar que conecta y cuenta**

Run: `python scripts/recalculate_evaluation_snapshots.py --dry-run`
Expected: imprime `Motor: SQLite local (IS_CLOUD=False)`, `Modo: DRY-RUN ...` y `Snapshots procesados: N` sin excepciones. (N puede ser 0 si la BD local está vacía; lo importante es que no falle.)

- [ ] **Step 3: Commit**

```bash
git add scripts/recalculate_evaluation_snapshots.py
git commit -m "feat: esqueleto de recalculate_evaluation_snapshots (conexion + lectura)"
```

---

## Task 3: Lógica de recálculo, comparación y UPDATE

**Files:**
- Modify: `scripts/recalculate_evaluation_snapshots.py`

**Interfaces:**
- Consumes: `parse_inputs_json`, `_FINANCIAL_KEYS`, `compute_financials`, `PLACEHOLDER` (de Task 2).
- Produces: script completo funcional con conteos `actualizados / sin cambios / omitidos / errores` y `UPDATE` transaccional.

- [ ] **Step 1: Reemplazar el cuerpo de `main()` (después de leer `rows`) con la lógica de recálculo**

Sustituir desde `print(f"Snapshots procesados: {len(rows)}")` hasta `return 0` por:

```python
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
                f"  evaluation_id={row['evaluation_id']} | {row['project_id']}\n"
                f"    hours_saved_per_month: {old_hours} -> {new_hours:.2f}\n"
                f"    annual_savings: {row.get('annual_savings')} -> {calc['annual_savings']:.2f}\n"
                f"    roi_first_year: {row.get('roi_first_year')} -> {calc['roi_first_year']:.2f}"
            )

    if pending and not args.dry_run:
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

    print(f"Snapshots procesados: {len(rows)}")
    print(f"  Actualizados: {updated}")
    print(f"  Sin cambios:  {unchanged}")
    print(f"  Omitidos:     {skipped} (inputs_json incompleto)")
    print(f"  Errores:      {errors}")
    if args.dry_run and pending:
        print(f"  (DRY-RUN: {len(pending)} filas se actualizarian en una corrida real)")
    return 0
```

- [ ] **Step 2: Test manual — sembrar un snapshot con `staff_count>1` en SQLite y verificar dry-run**

Run:
```bash
python -c "import json, sqlite3; from infra.db_migrations import run_migrations if False else None"
```
Luego, con un pequeño script inline (o REPL) insertar una fila de prueba en `project_viability.db` con `inputs_json` conteniendo `staff_count=200` y las 8 llaves de HI-DDD-0002, y `hours_saved_per_month=816.0`. Después:

Run: `python scripts/recalculate_evaluation_snapshots.py --dry-run --verbose`
Expected: reporta esa fila en `Actualizados: 1` con `816.0 -> 4.08` y NO escribe (la fila sigue en 816.0 tras el dry-run).

- [ ] **Step 3: Verificar que la corrida real SÍ escribe**

Run: `python scripts/recalculate_evaluation_snapshots.py --verbose`
Expected: `Actualizados: 1`; al re-leer la fila, `hours_saved_per_month == 4.08`. Correr el script otra vez debe dar `Actualizados: 0 / Sin cambios: 1` (idempotente).

- [ ] **Step 4: Commit**

```bash
git add scripts/recalculate_evaluation_snapshots.py
git commit -m "feat: recalculate aplica formula corregida y reescribe filas cambiadas"
```

---

## Task 4: Validación final contra Supabase

**Files:** ninguno (operación de validación)

- [ ] **Step 1: Correr suite completa de tests**

Run: `pytest tests/unit/test_financials.py -v`
Expected: todos PASS.

- [ ] **Step 2: Dry-run contra Supabase (con `DATABASE_URL` exportada)**

Asegurar `DATABASE_URL` apunta a Supabase, luego:

Run: `python scripts/recalculate_evaluation_snapshots.py --dry-run --verbose`
Expected: `Motor: Supabase (PostgreSQL, IS_CLOUD=True)` y un conteo de `Actualizados` acorde a los proyectos con `staff_count>1` (p.ej. LA-COPILOT-0001). Confirmar que los before/after tienen sentido.

- [ ] **Step 3: Backup de la tabla en Supabase**

Antes de escribir, exportar `project_evaluations` desde el dashboard de Supabase o `pg_dump`. (Paso manual — confirmar con la operadora.)

- [ ] **Step 4: Corrida real contra Supabase**

Run: `python scripts/recalculate_evaluation_snapshots.py --verbose`
Expected: `Actualizados: N` igual al conteo del dry-run; `Errores: 0`.

- [ ] **Step 5: Verificar HI-DDD-0002 en Supabase**

Consultar el snapshot de HI-DDD-0002: `hours_saved_per_month == 4.08`. Re-correr el script debe dar `Actualizados: 0` (idempotente).

---

## Self-Review

- **Spec coverage:** Fórmula (Task 1) ✓ · Tests parametrizados con staff_count>1 y HI-DDD-0002 (Task 1) ✓ · Script con adaptador/IS_CLOUD/PLACEHOLDER (Tasks 2–3) ✓ · Manejo str/dict de inputs_json (`parse_inputs_json`, Task 2) ✓ · dry-run sin commit (Task 3) ✓ · reporte con motor + conteos (Tasks 2–3) ✓ · backup + validación Supabase (Task 4) ✓.
- **Placeholder scan:** todos los steps de código incluyen el código real; el único paso manual (seed de prueba en Step 2 de Task 3, y backup en Task 4) está marcado como tal.
- **Type consistency:** `compute_financials` mantiene su firma; llaves de `inputs_json` idénticas a las de la firma; `_FINANCIAL_KEYS` cubre exactamente los 8 parámetros; `parse_inputs_json` definida en Task 2 y usada en Task 3.
