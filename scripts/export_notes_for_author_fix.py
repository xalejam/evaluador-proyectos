#!/usr/bin/env python3
"""
Exporta notas con effort_hours registradas para corregir el campo author.

Uso:
    python scripts/export_notes_for_author_fix.py            -> genera notas_horas_utf8.csv
    python scripts/export_notes_for_author_fix.py mi_archivo.csv

Edita solo la columna 'author_nuevo' en Excel.
Las columnas 'effort_hours' y demas son solo referencia — no se modifican al reimportar.
"""

import csv
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "project_viability.db"
OUTPUT_CSV = ROOT / "notas_reatribucion.csv"

FIELDS = [
    "note_id",
    "project_id",
    "project_name",
    "project_owner",
    "project_members",
    "author_actual",
    "author_nuevo",      # <- EDITAR ESTA COLUMNA
    "effort_hours",      # referencia, no se modifica
    "note_type",
    "created_at",
    "note_text_preview",
]


def export(db_path: str = str(DB_PATH), output_path: str = str(OUTPUT_CSV)) -> int:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        """
        SELECT
            pn.note_id,
            pn.project_id,
            COALESCE(p.name, '') AS project_name,
            COALESCE(p.owner, '') AS project_owner,
            pn.author AS author_actual,
            pn.effort_hours,
            pn.note_type,
            pn.created_at,
            pn.note_text
        FROM project_notes pn
        LEFT JOIN projects p
            ON p.project_id = pn.project_id OR p.id = pn.project_id
        WHERE pn.effort_hours IS NOT NULL AND pn.effort_hours > 0
        ORDER BY pn.project_id, pn.created_at
        """
    ).fetchall()

    # Construir lookup de miembros por proyecto
    member_rows = conn.execute(
        "SELECT project_id, member_name FROM project_members ORDER BY project_id, member_name"
    ).fetchall()
    conn.close()

    members_by_project: dict[str, list[str]] = {}
    for r in member_rows:
        members_by_project.setdefault(r["project_id"], []).append(r["member_name"])

    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for r in rows:
            pid = r["project_id"]
            members = members_by_project.get(pid, [])
            writer.writerow({
                "note_id": r["note_id"],
                "project_id": pid,
                "project_name": r["project_name"],
                "project_owner": r["project_owner"],
                "project_members": ", ".join(members) if members else "(sin miembros asignados)",
                "author_actual": r["author_actual"],
                "author_nuevo": r["author_actual"],  # pre-llenado igual al actual
                "effort_hours": r["effort_hours"],
                "note_type": r["note_type"],
                "created_at": r["created_at"],
                "note_text_preview": str(r["note_text"] or "")[:80],
            })

    print(f"Exportadas {len(rows)} notas con horas a: {output_path}")
    print("Edita la columna 'author_nuevo' en Excel y corre import_author_fix.py")
    return len(rows)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else str(OUTPUT_CSV)
    export(output_path=out)
