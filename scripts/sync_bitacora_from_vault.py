#!/usr/bin/env python3
"""Sincroniza bitacora.md del vault de Obsidian con project_notes en Supabase.

Uso:
    $env:DATABASE_URL = "postgresql://..."
    python scripts/sync_bitacora_from_vault.py --vault "C:\\ruta\\al\\vault"
"""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from domain.services.bitacora_sync_service import strip_git_userinfo, sync_bitacora_file  # noqa: E402
from infra.db.adapter import get_connection  # noqa: E402


def get_vault_repo_url(vault_root: Path) -> str | None:
    """Corre `git remote get-url origin` en la raíz del vault para armar los
    `loop_url` de cada proyecto. None si git no está disponible o el vault no
    tiene remoto — en ese caso el sync sigue igual, solo sin tocar loop_url."""
    try:
        result = subprocess.run(
            ["git", "-C", str(vault_root), "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return strip_git_userinfo(result.stdout.strip())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", required=True, help="Ruta al repo del vault de Obsidian")
    args = parser.parse_args()

    vault_root = Path(args.vault)
    bitacora_files = sorted(vault_root.glob("proyectos/*/bitacora.md"))
    if not bitacora_files:
        print(f"No se encontraron bitacora.md bajo {vault_root / 'proyectos'}")
        return 1

    vault_repo_url = get_vault_repo_url(vault_root)
    if not vault_repo_url:
        print("⚠ no se pudo obtener el remoto git del vault; no se sincroniza loop_url en esta corrida\n")

    conn = get_connection()
    total_pushed = total_pulled = total_estados = total_miembros = total_loop_urls = 0
    skipped: list[str] = []
    failed: list[str] = []
    try:
        for path in bitacora_files:
            rel = path.relative_to(vault_root)
            try:
                result = sync_bitacora_file(conn, path, vault_repo_url)
            except Exception as e:
                print(f"{rel}: ERROR - {e}")
                failed.append(f"{rel}: {e}")
                continue
            if result["skipped"]:
                skipped.append(f"{rel} (project_id={result['project_id']!r} no existe en Supabase)")
                continue
            total_pushed += result["pushed"]
            total_pulled += result["pulled"]
            estado_change = result.get("estado_change")
            loop_url_change = result.get("loop_url_change")
            has_output = (
                result["pushed"]
                or result["pulled"]
                or result.get("unknown_authors")
                or estado_change
                or result.get("responsable_agregado")
                or loop_url_change
                or result.get("metadata_warning")
            )
            if has_output:
                print(f"{rel}: +{result['pushed']} subidas, +{result['pulled']} bajadas")
            if result.get("unknown_authors"):
                print(f"  ⚠ autor(es) no registrados en project_members: {', '.join(result['unknown_authors'])}")
            if estado_change:
                total_estados += 1
                print(f"  estado: {estado_change['anterior']}→{estado_change['nuevo']} actualizado")
            if result.get("responsable_agregado"):
                total_miembros += 1
                print(f"  {result['responsable_agregado']} agregado a project_members")
            if loop_url_change:
                total_loop_urls += 1
                print("  loop_url actualizado")
            if result.get("metadata_warning"):
                print(f"  ⚠ {result['metadata_warning']}")
    finally:
        conn.close()

    print(
        f"\nTotal: {total_pushed} subidas, {total_pulled} bajadas, "
        f"{total_estados} estado(s) actualizado(s), {total_miembros} miembro(s) agregado(s), "
        f"{total_loop_urls} link(s) de documentación actualizado(s)."
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
