#!/usr/bin/env python3
"""Importa horas de esfuerzo desde CSV a project_notes."""

import csv
import io
import sqlite3
import sys
from pathlib import Path
from typing import Union

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "project_viability.db"


def import_hours(db_path: str, source: Union[str, io.StringIO]) -> dict:
    """
    Lee CSV con columnas [note_id, effort_hours] y actualiza project_notes.
    Retorna dict con claves: updated (int), rejected (int), rejected_rows (list).
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    existing_ids = {r[0] for r in conn.execute("SELECT note_id FROM project_notes").fetchall()}

    if isinstance(source, str):
        f = open(source, newline="", encoding="utf-8")
        close_file = True
    else:
        f = source
        close_file = False

    reader = csv.DictReader(f)
    updated = 0
    rejected = 0
    rejected_rows = []

    for row in reader:
        note_id_raw = str(row.get("note_id", "")).strip()
        hours_raw = str(row.get("effort_hours", "")).strip()

        try:
            note_id = int(note_id_raw)
        except ValueError:
            rejected += 1
            rejected_rows.append({"note_id": note_id_raw, "reason": "note_id no es entero"})
            continue

        if note_id not in existing_ids:
            rejected += 1
            rejected_rows.append({"note_id": note_id, "reason": "note_id no existe en BD"})
            continue

        if not hours_raw:
            rejected += 1
            rejected_rows.append({"note_id": note_id, "reason": "effort_hours vacío"})
            continue

        try:
            effort_hours = float(hours_raw)
        except ValueError:
            rejected += 1
            rejected_rows.append({"note_id": note_id, "reason": f"effort_hours no es número: {hours_raw!r}"})
            continue

        if effort_hours <= 0:
            rejected += 1
            rejected_rows.append({"note_id": note_id, "reason": f"effort_hours debe ser > 0 (fue {effort_hours})"})
            continue

        conn.execute(
            "UPDATE project_notes SET effort_hours = ? WHERE note_id = ?",
            (effort_hours, note_id),
        )
        updated += 1

    conn.commit()
    conn.close()
    if close_file:
        f.close()

    return {"updated": updated, "rejected": rejected, "rejected_rows": rejected_rows}


def _print_report(result: dict) -> None:
    print(f"Actualizadas: {result['updated']:>5} notas")
    print(f"Rechazadas:   {result['rejected']:>5} notas")
    if result["rejected_rows"]:
        for r in result["rejected_rows"]:
            print(f"  → note_id {r['note_id']}: {r['reason']}")


if __name__ == "__main__":
    csv_path = sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "notas_horas.csv")
    result = import_hours(str(DB_PATH), csv_path)
    _print_report(result)
    if result["rejected"] > 0:
        sys.exit(1)
