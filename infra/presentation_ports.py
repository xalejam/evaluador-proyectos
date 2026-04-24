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
    DB_PATH,
    ProjectStatus,
    build_presentation_bytes,
    fetch_executing_projects,
)

__all__ = [
    "DataSource",
    "FileDestination",
    "SqliteDataSource",
    "InMemoryDestination",
    "ProjectStatus",
    "build_presentation_bytes",
]


@runtime_checkable
class DataSource(Protocol):
    def fetch_projects(self) -> list[ProjectStatus]: ...


@runtime_checkable
class FileDestination(Protocol):
    def save(self, data: bytes) -> bytes | str:
        """Retorna bytes (download_button) o str URL (link_button en nube)."""
        ...


class SqliteDataSource:
    """Fuente de datos local: lee proyectos en ejecución de SQLite."""

    def __init__(self, db_path: Path = DB_PATH) -> None:
        self._db_path = db_path

    def fetch_projects(self) -> list[ProjectStatus]:
        return fetch_executing_projects(self._db_path)


class InMemoryDestination:
    """Destino local: devuelve los bytes para que Streamlit sirva la descarga."""

    def save(self, data: bytes) -> bytes:
        return data


# ---------------------------------------------------------------------------
# Stubs futuros — NO implementar hasta tener plataforma definida
# ---------------------------------------------------------------------------
# class AzureBlobDestination:
#     def __init__(self, container: str, blob_name: str) -> None: ...
#     def save(self, data: bytes) -> str: ...   # retorna URL blob
#
# class DatabricksDestination:
#     def __init__(self, dbfs_path: str) -> None: ...
#     def save(self, data: bytes) -> str: ...   # retorna URL DBFS
