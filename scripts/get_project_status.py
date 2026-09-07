#!/usr/bin/env python3
"""Consulta el status de un proyecto en Supabase. Solo lectura.

Usado por /nuevo-proyecto (vault de Obsidian, repo separado) para resolver
el `estado` inicial de un index.md nuevo — ver
docs/superpowers/specs/2026-09-04-estado-inicial-nuevo-proyecto-design.md
en el vault.

Uso:
    $env:DATABASE_URL = "postgresql://..."
    python scripts/get_project_status.py --project-id MX-DDD-0005

Imprime una sola línea: el valor de `status` si el project_id existe, o
NOT_FOUND si no. Nunca escribe en la base de datos.
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from domain.services.bitacora_sync_service import get_project_status  # noqa: E402
from infra.db.adapter import get_connection  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-id", required=True)
    args = parser.parse_args()

    conn = get_connection()
    try:
        status = get_project_status(conn, args.project_id)
    finally:
        conn.close()

    print(status if status is not None else "NOT_FOUND")
    return 0


if __name__ == "__main__":
    sys.exit(main())
