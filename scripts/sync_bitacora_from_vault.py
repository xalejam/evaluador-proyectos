#!/usr/bin/env python3
"""Sincroniza bitacora.md del vault de Obsidian con project_notes en Supabase.

Uso:
    $env:DATABASE_URL = "postgresql://..."
    python scripts/sync_bitacora_from_vault.py --vault "C:\\ruta\\al\\vault"
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from domain.services.bitacora_sync_service import sync_bitacora_file  # noqa: E402
from infra.db.adapter import get_connection  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", required=True, help="Ruta al repo del vault de Obsidian")
    args = parser.parse_args()

    vault_root = Path(args.vault)
    bitacora_files = sorted(vault_root.glob("proyectos/*/bitacora.md"))
    if not bitacora_files:
        print(f"No se encontraron bitacora.md bajo {vault_root / 'proyectos'}")
        return 1

    conn = get_connection()
    total_pushed = total_pulled = total_estados = total_miembros = 0
    skipped: list[str] = []
    failed: list[str] = []
    try:
        for path in bitacora_files:
            rel = path.relative_to(vault_root)
            try:
                result = sync_bitacora_file(conn, path)
            except Exception as e:
                print(f"{rel}: ERROR - {e}")
                failed.append(f"{rel}: {e}")
                continue
            if result["skipped"]:
                skipped.append(f"{rel} (project_id={result['project_id']!r} no existe en Supabase)")
                continue
            total_pushed += result["pushed"]
            total_pulled += result["pulled"]
            if result["pushed"] or result["pulled"]:
                print(f"{rel}: +{result['pushed']} subidas, +{result['pulled']} bajadas")
            if result.get("unknown_authors"):
                print(f"  ⚠ autor(es) no registrados en project_members: {', '.join(result['unknown_authors'])}")
            estado_change = result.get("estado_change")
            if estado_change:
                total_estados += 1
                print(f"  estado: {estado_change['anterior']}→{estado_change['nuevo']} actualizado")
            if result.get("responsable_agregado"):
                total_miembros += 1
                print(f"  {result['responsable_agregado']} agregado a project_members")
            if result.get("metadata_warning"):
                print(f"  ⚠ {result['metadata_warning']}")
    finally:
        conn.close()

    print(
        f"\nTotal: {total_pushed} subidas, {total_pulled} bajadas, "
        f"{total_estados} estado(s) actualizado(s), {total_miembros} miembro(s) agregado(s)."
    )
    if skipped:
        print(f"\n{len(skipped)} archivo(s) sin sincronizar (proyecto no dado de alta en Supabase):")
        for line in skipped:
            print(f"  - {line}")
    if failed:
        print(f"\n{len(failed)} archivo(s) con error durante la sincronización:")
        for line in failed:
            print(f"  - {line}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
