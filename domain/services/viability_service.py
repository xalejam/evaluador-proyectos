"""Servicio de viabilidad (computo + persistencia de acciones)."""

from __future__ import annotations

from typing import Any

import streamlit as st

from domain.exceptions import ValidationError
from infra.db.connection import get_sqlite_conn
from infra.db.migrations import ensure_schema
from infra.db.repositories.evaluation_repo import EvaluationRepository
from infra.db.repositories.project_repo import ProjectRepository
from infra.integrations.use_case_matrix_sync import sync_to_use_case_matrix


class ViabilityService:
    def __init__(self, db_path: str = "project_viability.db") -> None:
        self.db_path = db_path
        self.project_repo = ProjectRepository(db_path)
        self.evaluation_repo = EvaluationRepository(db_path)

    @staticmethod
    def compute_viability(inputs: dict[str, Any]) -> dict[str, Any]:
        # Reusa calculadora legacy para no romper behavior.
        return st.session_state.calculator.calculate_viability(inputs)

    def save_evaluation(
        self,
        inputs: dict[str, Any],
        calc_results: dict[str, Any],
        status_after: str,
        author: str,
        project_id: str | None = None,
        loop_url: str | None = None,
        delivery_team: str | None = None,
    ) -> str:
        with get_sqlite_conn(self.db_path) as conn:
            ensure_schema(conn)

        # Persistencia principal la sigue haciendo el flujo legacy del manager/calculator.
        if project_id and st.session_state.excel_manager.project_exists(project_id):
            final_project_id, calc_results = st.session_state.calculator.update_project(project_id, inputs)
        else:
            final_project_id, calc_results = st.session_state.calculator.create_project(inputs)

        self.project_repo.update_status(final_project_id, status_after, loop_url=loop_url, delivery_team=delivery_team)
        self.evaluation_repo.insert_snapshot(
            project_id=final_project_id,
            action="recalc_saved" if project_id else "evaluation_saved",
            status_after=status_after,
            calc_results=calc_results,
            inputs_json=inputs,
            created_by=author,
        )
        sync_to_use_case_matrix(final_project_id, inputs, calc_results)
        return final_project_id

    def approve_project(
        self,
        inputs: dict[str, Any],
        calc_results: dict[str, Any],
        loop_url: str,
        author: str,
        project_id: str | None = None,
        delivery_team: str | None = None,
    ) -> str:
        if not (loop_url or "").strip():
            raise ValidationError("loop_url", "es obligatorio para aprobar")

        if project_id and st.session_state.excel_manager.project_exists(project_id):
            final_project_id, calc_results = st.session_state.calculator.update_project(project_id, inputs)
        else:
            final_project_id, calc_results = st.session_state.calculator.create_project(inputs)

        self.project_repo.update_status(final_project_id, "approved", loop_url=loop_url, delivery_team=delivery_team)
        self.evaluation_repo.insert_snapshot(
            project_id=final_project_id,
            action="approved",
            status_after="approved",
            calc_results=calc_results,
            inputs_json=inputs,
            created_by=author,
        )
        sync_to_use_case_matrix(final_project_id, inputs, calc_results)
        return final_project_id
