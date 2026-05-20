#!/usr/bin/env python3
"""
Reimporta el CSV editado y actualiza el campo author en project_notes.
Solo actualiza filas donde 'author_nuevo' difiere de 'author_actual'.
Las horas NO se modifican.

Uso:
    python scripts/import_author_fix.py                      -> lee notas_reatribucion.csv
    python scripts/import_author_fix.py mi_archivo.csv
"""

import csv
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "project_viability.db"
INPUT_CSV = ROOT / "notas_reatribucion.csv"


def import_author_fix(db_path: str = str(DB_PATH), csv_path: str = str(INPUT_CSV)) -> dict:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    existing_ids = {r[0] for r in conn.execute("SELECT note_id FROM project_notes").fetchall()}

    updated = 0
    skipped = 0
    rejected = 0
    rejected_rows = []

    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            note_id_raw = str(row.get("note_id", "")).strip()
            author_actual = str(row.get("author_actual", "")).strip()
            author_nuevo = str(row.get("author_nuevo", "")).strip()

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

            if not author_nuevo:
                rejected += 1
                rejected_rows.append({"note_id": note_id, "reason": "author_nuevo está vacío"})
                continue

            if author_nuevo == author_actual:
                skipped += 1
                continue

            conn.execute(
                "UPDATE project_notes SET author = ? WHERE note_id = ?",
                (author_nuevo, note_id),
            )
            updated += 1

    conn.commit()
    conn.close()

    return {
        "updated": updated,
        "skipped": skipped,
        "rejected": rejected,
        "rejected_rows": rejected_rows,
    }


def _print_report(result: dict) -> None:
    print(f"Actualizadas: {result['updated']:>5} notas (author cambiado)")
    print(f"Sin cambio:   {result['skipped']:>5} notas (author_nuevo == author_actual)")
    print(f"Rechazadas:   {result['rejected']:>5} notas")
    if result["rejected_rows"]:
        for r in result["rejected_rows"]:
            print(f"  → note_id {r['note_id']}: {r['reason']}")


if __name__ == "__main__":
    csv_path = sys.argv[1] if len(sys.argv) > 1 else str(INPUT_CSV)
    result = import_author_fix(csv_path=csv_path)
    _print_report(result)
    if result["rejected"] > 0:
        sys.exit(1)
