#!/usr/bin/env python3
"""
Administración de usuarios del Evaluador de Proyectos.

Uso:
    python scripts/create_user.py --email ana@kantar.com --password temporal123
    python scripts/create_user.py --email ana@kantar.com --deactivate
    python scripts/create_user.py --list
"""

import argparse
import getpass
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import bcrypt
from infra.db.connection import get_sqlite_conn, DB_PATH
from infra.db.adapter import PLACEHOLDER


def _ensure_users_table(conn) -> None:
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now'))
        )
        """
    )
    conn.commit()


def create_user(email: str, password: str) -> None:
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    with get_sqlite_conn(DB_PATH) as conn:
        _ensure_users_table(conn)
        conn.execute(
            f"INSERT INTO users (email, password_hash) VALUES ({PLACEHOLDER}, {PLACEHOLDER}) "
            f"ON CONFLICT(email) DO UPDATE SET password_hash={PLACEHOLDER}, is_active=1",
            (email.lower(), hashed, hashed),
        )
        conn.commit()
    print(f"Usuario creado/actualizado: {email}")


def deactivate_user(email: str) -> None:
    with get_sqlite_conn(DB_PATH) as conn:
        _ensure_users_table(conn)
        conn.execute(
            f"UPDATE users SET is_active=0 WHERE email={PLACEHOLDER}",
            (email.lower(),),
        )
        conn.commit()
    print(f"Usuario desactivado: {email}")


def list_users() -> None:
    with get_sqlite_conn(DB_PATH) as conn:
        _ensure_users_table(conn)
        rows = conn.execute(
            "SELECT email, is_active, created_at FROM users ORDER BY email"
        ).fetchall()
    if not rows:
        print("No hay usuarios registrados.")
        return
    print(f"{'Email':<40} {'Activo':<8} {'Creado'}")
    print("-" * 70)
    for r in rows:
        activo = "Sí" if r[1] else "No"
        print(f"{r[0]:<40} {activo:<8} {r[2]}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Gestión de usuarios del Evaluador")
    parser.add_argument("--email", help="Correo del usuario")
    parser.add_argument("--password", help="Contraseña (opcional — se solicitará si no se provee)")
    parser.add_argument("--deactivate", action="store_true", help="Desactivar usuario")
    parser.add_argument("--list", action="store_true", help="Listar todos los usuarios")
    args = parser.parse_args()

    if args.list:
        list_users()
    elif args.deactivate:
        if not args.email:
            parser.error("--email es requerido con --deactivate")
        deactivate_user(args.email)
    elif args.email:
        password = args.password or getpass.getpass("Contraseña: ")
        create_user(args.email, password)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
