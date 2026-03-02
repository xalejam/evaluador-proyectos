"""Integracion de sincronizacion con Use Case Matrix.

Se mantiene encapsulada para dispararse solo en acciones de guardado/aprobacion.
"""

from __future__ import annotations

from ui.tabs.planning import sync_to_use_case_matrix as _legacy_sync


def sync_to_use_case_matrix(project_id: str, project_payload: dict, calc_results: dict) -> None:
    _legacy_sync(project_id, project_payload, calc_results)
