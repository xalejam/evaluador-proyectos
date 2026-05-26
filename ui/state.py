"""Manejo centralizado de session_state para UI Streamlit."""

from __future__ import annotations

import streamlit as st

DEFAULTS = {
    "language": "es",
    "edit_mode": False,
    "selected_project_id": None,
    "temp_calculation": None,
    "latest_results": None,
    "active_tab": 0,
}


def init_state() -> None:
    for key, value in DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_temp_calculation() -> None:
    st.session_state.temp_calculation = None


def set_selected_project(project_id: str | None) -> None:
    st.session_state.selected_project_id = project_id


def get_author_default() -> str:
    return str(st.session_state.get("author", st.session_state.get("current_user", "Xiomara Monroy")))
