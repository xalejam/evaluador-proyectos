"""Adapter ports para generación de presentaciones — extensible a nube."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Protocol, runtime_checkable

# Agrega scripts/ al path para poder importar el generador sin moverlo
_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from generate_execution_status_presentation import (  # noqa: E402
    ProjectStatus,
    build_presentation_bytes,
)

DB_PATH = Path(__file__).resolve().parent.parent / "project_viability.db"

__all__ = [
    "DataSource",
    "FileDestination",
    "SqliteDataSource",
    "InMemoryDestination",
    "ProjectStatus",
    "build_presentation_bytes",
]

# ---------------------------------------------------------------------------
# SQL portable: funciona en SQLite (local) y PostgreSQL (Supabase/Cloud).
# Inlinea v_project_progress_history y elimina datetime() exclusivo de SQLite.
# ---------------------------------------------------------------------------
_PPTX_SQL = """
WITH progress_history AS (
    SELECT project_id, progress_percent, created_at
    FROM (
        SELECT project_id, progress_percent, created_at, entry_group_id,
               ROW_NUMBER() OVER (
                   PARTITION BY entry_group_id
                   ORDER BY note_id ASC
               ) AS rn_grp
        FROM project_notes
        WHERE progress_percent IS NOT NULL
    ) deduped
    WHERE rn_grp = 1
),
latest_progress AS (
    SELECT h.project_id, h.progress_percent, h.created_at
    FROM progress_history h
    JOIN (
        SELECT project_id, MAX(created_at) AS max_created_at
        FROM progress_history
        GROUP BY project_id
    ) mx ON mx.project_id = h.project_id
         AND mx.max_created_at = h.created_at
),
latest_notes AS (
    SELECT project_id, note_type, note_text, created_at,
        ROW_NUMBER() OVER (
            PARTITION BY project_id, note_type
            ORDER BY created_at DESC, note_id DESC
        ) AS rn
    FROM project_notes
)
SELECT
    p.project_id,
    p.name,
    lp.progress_percent,
    lp.created_at    AS progress_at,
    COALESCE(gn.note_text, '') AS general_note,
    COALESCE(pn.note_text, '') AS next_step,
    COALESCE(bn.note_text, '') AS blocker,
    COALESCE(rk.note_text, '') AS risk
FROM projects p
LEFT JOIN latest_progress lp ON lp.project_id = p.project_id
LEFT JOIN latest_notes gn ON gn.project_id = p.project_id AND gn.note_type = 'general'       AND gn.rn = 1
LEFT JOIN latest_notes pn ON pn.project_id = p.project_id AND pn.note_type = 'proximo_paso'  AND pn.rn = 1
LEFT JOIN latest_notes bn ON bn.project_id = p.project_id AND bn.note_type = 'bloqueador'    AND bn.rn = 1
LEFT JOIN latest_notes rk ON rk.project_id = p.project_id AND rk.note_type = 'riesgo'       AND rk.rn = 1
WHERE lower(COALESCE(p.status, '')) = 'executing'
ORDER BY COALESCE(lp.created_at, p.updated_at, p.created_date) DESC, p.project_id
"""


@runtime_checkable
class DataSource(Protocol):
    def fetch_projects(self) -> list[ProjectStatus]: ...


@runtime_checkable
class FileDestination(Protocol):
    def save(self, data: bytes) -> bytes | str:
        """Retorna bytes (download_button) o str URL (link_button en nube)."""
        ...


class SqliteDataSource:
    """Fuente de datos para proyectos en ejecución.

    Usa infra.db.adapter.get_connection() que resuelve automáticamente
    a SQLite en local o PostgreSQL (Supabase) en Cloud.
    """

    def __init__(self, db_path: Path = DB_PATH) -> None:
        self._db_path = Path(db_path).resolve()

    def fetch_projects(self) -> list[ProjectStatus]:
        import pandas as pd

        from infra.db.adapter import db_read_dataframe, get_connection

        conn = get_connection(local_path=str(self._db_path))
        df = db_read_dataframe(conn, _PPTX_SQL)
        conn.close()

        if df.empty:
            return []

        # PostgreSQL retorna progress_percent como float nullable → int|None
        df["progress_percent"] = df["progress_percent"].apply(
            lambda x: int(x) if x is not None and not pd.isna(x) else None
        )
        # PostgreSQL retorna created_at como Timestamp → str ISO para el dataclass
        df["progress_at"] = df["progress_at"].apply(
            lambda x: x.isoformat() if hasattr(x, "isoformat") else (str(x) if x is not None else None)
        )

        return [ProjectStatus(**row) for row in df.to_dict(orient="records")]


class InMemoryDestination:
    """Destino local: devuelve los bytes para que Streamlit sirva la descarga."""

    def save(self, data: bytes) -> bytes:
        return data
