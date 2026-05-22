#!/usr/bin/env python3
"""Exporta notas sin effort_hours a CSV para backfill manual."""

import csv
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "project_viability.db"
OUTPUT_CSV = ROOT / "notas_horas.csv"

FIELDS = ["note_id", "project_id", "note_type", "note_title", "created_at", "note_text", "effort_hours"]


def export_notes(db_path: str = str(DB_PATH), output_path: str = str(OUTPUT_CSV)) -> int:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT note_id, project_id, note_type, note_title, created_at, note_text
        FROM project_notes
        WHERE effort_hours IS NULL
        ORDER BY project_id, created_at
        """).fetchall()
    conn.close()

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for r in rows:
            writer.writerow({**dict(r), "effort_hours": ""})

    print(f"Exportadas {len(rows)} notas a {output_path}")
    return len(rows)


if __name__ == "__main__":
    export_notes()
