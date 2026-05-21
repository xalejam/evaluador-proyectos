# main.py
"""
Archivo principal del Sistema de Evaluacion de Viabilidad - Bilingue
Une todos los modulos: planificacion, seguimiento, dashboard, feedback y SQL.
"""

import streamlit as st
from pathlib import Path
from ui.login import render_login
from ui.tabs.shared import (
    t, init_excel_manager, render_language_selector,
    render_sidebar_stats
)
from ui.state import init_state
from ui.tabs.planning import render_planning_tab as render_viabilidad_tab
from ui.tabs.tracking import render_tracking_tab as render_post_impl_tab
from ui.tabs.dashboard import render_dashboard as render_dashboard_tab
from ui.tabs.feedback_processor import render_feedback_processor as render_feedback_tab
from ui.tabs.sql_queries import render_sql_queries_tab as render_sql_tab
from ui.use_case_matrix import render_use_case_matrix_tab
from ui.tabs.seguimiento_operativo import render_seguimiento_operativo as render_seguimiento_operativo_tab
from infra.db_migrations import ensure_all_operational_schema
from infra.db.connection import get_sqlite_conn, DB_PATH

ROOT = Path(__file__).resolve().parent

# Configuracion de Streamlit
st.set_page_config(
    page_title="Evaluador de Viabilidad Bilingue",
    page_icon=":abacus:",
    layout="wide"
)


def main():
    """Funcion principal."""
    if not render_login():
        st.stop()

    # Inicializar sistema
    init_state()
    init_excel_manager()

    with get_sqlite_conn(DB_PATH) as conn:
        ensure_all_operational_schema(conn)
        conn.commit()

    # Logo arriba a la izquierda (sidebar)
    logo_path = ROOT / "assets_images" / "logo_DDNola.png"
    if logo_path.exists():
        st.sidebar.image(str(logo_path), use_container_width=True)

    # Selector de idioma (siempre arriba en sidebar)
    render_language_selector()

    # Titulo principal
    st.title(t("platform_title"))
    st.markdown(t("platform_subtitle"))

    # Componentes del sidebar
    render_sidebar_stats()

    # Cerrar sesión
    st.sidebar.divider()
    user_email = st.session_state.get("user_email", "")
    st.sidebar.caption(f"Sesión: {user_email}")
    if st.sidebar.button("Cerrar sesión"):
        st.session_state.clear()
        st.rerun()

    # Pestanas principales
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        t("viability_tab"),
        t("operational_log_tab"),
        t("impact_kpis_tab"),
        t("dashboard_tab"),
        t("use_case_matrix_tab"),
        t("feedback_tab"),
        t("sql_tab"),
    ])

    with tab1:
        render_viabilidad_tab()

    with tab2:
        render_seguimiento_operativo_tab()

    with tab3:
        render_post_impl_tab()

    with tab4:
        render_dashboard_tab()

    with tab5:
        render_use_case_matrix_tab()

    with tab6:
        render_feedback_tab()

    with tab7:
        render_sql_tab()


if __name__ == "__main__":
    main()
