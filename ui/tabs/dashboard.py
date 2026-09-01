# dashboard.py
"""
Módulo de dashboard con métricas generales y visualizaciones
"""

import pandas as pd
import plotly.express as px
import streamlit as st

from infra.db.connection import DB_PATH as PV_DB_PATH
from infra.db.connection import get_sqlite_conn
from ui.tabs.shared import t


def _safe_number(value, default=0):
    """Convierte un valor a número de forma segura."""
    if value is None:
        return default
    try:
        return float(value) if isinstance(value, str) else value or default
    except (ValueError, TypeError):
        return default


def _load_projects_from_db() -> list[dict]:
    """Carga proyectos desde project_viability.db como lista de dicts."""
    with get_sqlite_conn(PV_DB_PATH) as conn:
        try:
            rows = conn.execute("SELECT * FROM projects WHERE status IS NOT NULL ORDER BY updated_at DESC").fetchall()
            projects = []
            for r in rows:
                if isinstance(r, dict):
                    projects.append(r)
                else:
                    projects.append(dict(r))
            return projects
        except Exception as e:
            import logging

            logging.getLogger(__name__).error("Error cargando proyectos: %s", e, exc_info=True)
            return []


def render_dashboard():
    """Dashboard con métricas generales"""
    st.header(t("general_dashboard"))

    projects = _load_projects_from_db()

    if not projects:
        st.warning(t("no_projects_dashboard"))
        return

    # Métricas principales
    col1, col2, col3, col4 = st.columns(4)

    total_projects = len(projects)
    dict_projects = [p for p in projects if isinstance(p, dict)]
    avg_viability = (
        sum(_safe_number(p.get("viability_score")) for p in dict_projects) / len(dict_projects) if dict_projects else 0
    )
    total_savings = sum(_safe_number(p.get("annual_savings")) for p in dict_projects)
    high_priority = len([p for p in dict_projects if p.get("priority") == t("priority_high")])

    with col1:
        st.metric(t("total_projects"), total_projects)
    with col2:
        st.metric(t("avg_score"), f"{avg_viability:.1f}/100")
    with col3:
        st.metric(t("total_savings"), f"${total_savings:,.0f}")
    with col4:
        st.metric(t("high_priority"), high_priority)

    # Row de gráficos principales
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        # Gráfico de distribución de scores
        st.subheader(t("dashboard_scores_distribution"))

        scores = [_safe_number(p.get("viability_score")) for p in projects if isinstance(p, dict)]
        fig_hist = px.histogram(
            x=scores,
            nbins=10,
            title=t("dashboard_scores_distribution_title"),
            labels={"x": t("viability_score"), "y": t("dashboard_num_projects")},
            color_discrete_sequence=["#636EFA"],
        )
        fig_hist.update_layout(showlegend=False, height=350)
        st.plotly_chart(fig_hist, use_container_width=True)

    with col_chart2:
        # Gráfico de prioridades
        st.subheader(t("dashboard_priority_distribution"))

        priorities = [p.get("priority") for p in projects if isinstance(p, dict) and p.get("priority")]
        priority_counts = pd.Series(priorities).value_counts()

        # Colores para cada prioridad
        colors = {
            t("priority_high"): "#00CC96",
            t("priority_medium_high"): "#00B8D4",
            t("priority_medium"): "#FFA726",
            t("priority_low"): "#FF6B6B",
        }

        if not priority_counts.empty:
            fig_pie = px.pie(
                values=priority_counts.values,
                names=priority_counts.index,
                title=t("dashboard_projects_by_priority"),
                color=priority_counts.index,
                color_discrete_map=colors,
            )
            fig_pie.update_layout(height=350)
            st.plotly_chart(fig_pie, use_container_width=True)

    # Gráfico de ROI vs Score (si hay más de un proyecto)
    if len(projects) > 1:
        st.subheader(t("dashboard_viability_vs_roi"))

        df_scatter = pd.DataFrame(
            [
                {
                    "Score": _safe_number(p.get("viability_score")),
                    "ROI (%)": _safe_number(p.get("roi_first_year")),
                    "Proyecto": p.get("name") or "",
                    "Prioridad": p.get("priority") or "",
                    "Ahorro Anual": _safe_number(p.get("annual_savings")),
                }
                for p in projects
                if isinstance(p, dict)
            ]
        )

        fig_scatter = px.scatter(
            df_scatter,
            x="Score",
            y="ROI (%)",
            color="Prioridad",
            size="Ahorro Anual",
            hover_data=["Proyecto"],
            title=t("dashboard_viability_roi_relation"),
            color_discrete_map=colors,
        )
        fig_scatter.update_layout(height=400)
        st.plotly_chart(fig_scatter, use_container_width=True)

    # Análisis de factores (nuevo)
    st.subheader(t("dashboard_factor_analysis"))

    col_factors1, col_factors2 = st.columns(2)

    with col_factors1:
        # Distribución de complejidad
        complexity_levels = [
            p.get("implementation_complexity")
            for p in projects
            if isinstance(p, dict) and p.get("implementation_complexity") is not None
        ]
        if complexity_levels:
            complexity_counts = pd.Series(complexity_levels).value_counts().sort_index()

            fig_complexity = px.bar(
                x=complexity_counts.index,
                y=complexity_counts.values,
                title=t("dashboard_complexity_distribution_title"),
                labels={"x": t("dashboard_complexity_level"), "y": t("dashboard_num_projects")},
                color=complexity_counts.values,
                color_continuous_scale="RdYlGn_r",
            )
            fig_complexity.update_layout(showlegend=False, height=300)
            st.plotly_chart(fig_complexity, use_container_width=True)

    with col_factors2:
        # Distribución de riesgo
        risk_levels = [p.get("risk_level") for p in projects if isinstance(p, dict) and p.get("risk_level") is not None]
        if risk_levels:
            risk_counts = pd.Series(risk_levels).value_counts().sort_index()

            fig_risk = px.bar(
                x=risk_counts.index,
                y=risk_counts.values,
                title=t("dashboard_technical_risk_distribution_title"),
                labels={"x": t("dashboard_risk_level"), "y": t("dashboard_num_projects")},
                color=risk_counts.values,
                color_continuous_scale="RdYlGn_r",
            )
            fig_risk.update_layout(showlegend=False, height=300)
            st.plotly_chart(fig_risk, use_container_width=True)

    # Tabla detallada de proyectos
    st.subheader(t("all_projects"))

    # Preparar datos para la tabla
    df_data = []
    for p in projects:
        if not isinstance(p, dict):
            continue
        df_data.append(
            {
                "ID": p.get("id") or p.get("project_id") or "",
                t("project_name_col"): p.get("name") or "",
                t("priority"): p.get("priority") or "",
                t("score_col"): f"{_safe_number(p.get('viability_score'))}/100",
                "ROI %": f"{_safe_number(p.get('roi_first_year')):.1f}%",
                t("annual_savings_col"): f"${_safe_number(p.get('annual_savings')):,.0f}",
                "Complejidad": f"{_safe_number(p.get('implementation_complexity'))}/5",
                "Riesgo": f"{_safe_number(p.get('risk_level'))}/5",
                t("status_col"): t("status_implemented") if p.get("status") == "implemented" else t("status_planning"),
            }
        )
    df_display = pd.DataFrame(df_data) if df_data else pd.DataFrame()

    # Configurar colores para la tabla basados en prioridad
    def highlight_priority(row):
        priority = row[t("priority")]
        if priority == t("priority_high"):
            return ["background-color: #E8F5E8"] * len(row)
        elif priority == t("priority_medium_high"):
            return ["background-color: #E3F2FD"] * len(row)
        elif priority == t("priority_medium"):
            return ["background-color: #FFF3E0"] * len(row)
        elif priority == t("priority_low"):
            return ["background-color: #FFEBEE"] * len(row)
        else:
            return [""] * len(row)

    styled_df = df_display.style.apply(highlight_priority, axis=1)
    st.dataframe(styled_df, use_container_width=True, hide_index=True)

    # Métricas de seguimiento desde base de datos
    try:
        trackings = st.session_state.excel_manager.tracking_df
    except Exception:
        trackings = pd.DataFrame()

    if len(trackings) > 0:
        st.subheader(t("dashboard_tracking_metrics"))

        col_track1, col_track2, col_track3, col_track4, col_track5 = st.columns(5)

        # Calcular métricas de seguimiento
        avg_performance = trackings["performance_score"].mean()
        avg_efficiency = trackings["efficiency_ratio"].mean()
        avg_adoption = trackings["adoption_rate"].mean()
        avg_satisfaction = trackings["user_satisfaction_score"].mean()
        if "survey_time_saved_percent" in trackings.columns:
            avg_reported_time_saved = trackings["survey_time_saved_percent"].mean()
        else:
            avg_reported_time_saved = None

        with col_track1:
            st.metric(t("dashboard_avg_performance"), f"{avg_performance:.0f}/100")
        with col_track2:
            st.metric(t("dashboard_avg_efficiency"), f"{avg_efficiency:.2f}x")
        with col_track3:
            st.metric(t("dashboard_avg_adoption"), f"{avg_adoption:.0f}%")
        with col_track4:
            st.metric(t("dashboard_avg_satisfaction"), f"{avg_satisfaction:.1f}/10")
        with col_track5:
            if avg_reported_time_saved is None or pd.isna(avg_reported_time_saved):
                st.metric(t("dashboard_avg_reported_time_saved"), "N/A")
            else:
                st.metric(t("dashboard_avg_reported_time_saved"), f"{avg_reported_time_saved:.1f}%")

        has_feedback_columns = {"nps_score", "usage_frequency"}.issubset(set(trackings.columns))
        if has_feedback_columns:
            feedback_df = trackings.copy()
            feedback_df["nps_score"] = pd.to_numeric(feedback_df["nps_score"], errors="coerce")
            feedback_df = feedback_df[feedback_df["nps_score"].between(0, 10)]

            if not feedback_df.empty:
                st.subheader(t("dashboard_feedback_metrics"))

                promoters = int((feedback_df["nps_score"] >= 9).sum())
                passives = int(feedback_df["nps_score"].between(7, 8).sum())
                detractors = int((feedback_df["nps_score"] <= 6).sum())
                total_nps = len(feedback_df)
                pct_promoters = (promoters / total_nps * 100) if total_nps else 0
                pct_passives = (passives / total_nps * 100) if total_nps else 0
                pct_detractors = (detractors / total_nps * 100) if total_nps else 0
                nps_net = pct_promoters - pct_detractors

                col_fb1, col_fb2, col_fb3 = st.columns(3)
                with col_fb1:
                    st.metric(t("dashboard_avg_nps"), f"{feedback_df['nps_score'].mean():.1f}/10")
                with col_fb2:
                    st.metric(t("dashboard_nps_net"), f"{nps_net:.0f}")
                with col_fb3:
                    st.metric(
                        t("dashboard_nps_segments"),
                        f"{pct_promoters:.0f}% / {pct_passives:.0f}% / {pct_detractors:.0f}%",
                    )

                col_fb_chart1, col_fb_chart2 = st.columns(2)
                with col_fb_chart1:
                    frequency_series = feedback_df["usage_frequency"].fillna("").astype(str).str.strip()
                    frequency_series = frequency_series[frequency_series != ""]
                    if not frequency_series.empty:
                        freq_counts = frequency_series.value_counts()
                        fig_freq = px.pie(
                            values=freq_counts.values,
                            names=freq_counts.index,
                            title=t("dashboard_usage_frequency_distribution"),
                        )
                        fig_freq.update_layout(height=350)
                        st.plotly_chart(fig_freq, use_container_width=True)

                with col_fb_chart2:
                    feedback_scatter = feedback_df.dropna(subset=["user_satisfaction_score", "nps_score"]).copy()
                    if not feedback_scatter.empty:
                        feedback_scatter["user_satisfaction_score"] = pd.to_numeric(
                            feedback_scatter["user_satisfaction_score"], errors="coerce"
                        )
                        feedback_scatter = feedback_scatter.dropna(subset=["user_satisfaction_score"])
                        if not feedback_scatter.empty:
                            fig_nps_sat = px.scatter(
                                feedback_scatter,
                                x="user_satisfaction_score",
                                y="nps_score",
                                color="usage_frequency",
                                title=t("dashboard_nps_vs_satisfaction"),
                                labels={
                                    "user_satisfaction_score": t("feedback_satisfaction_metric"),
                                    "nps_score": t("feedback_nps_metric"),
                                    "usage_frequency": t("feedback_frequency_metric"),
                                },
                            )
                            fig_nps_sat.update_layout(height=350)
                            st.plotly_chart(fig_nps_sat, use_container_width=True)
            else:
                st.info(t("dashboard_no_feedback_data"))
        else:
            st.info(t("dashboard_no_feedback_data"))

        # Gráfico de performance vs score inicial
        if len(trackings) > 1:
            tracking_projects = []
            for _, tracking in trackings.iterrows():
                project = next(
                    (p for p in projects if (p.get("project_id") or p.get("id")) == tracking["project_id"]), None
                )
                if project:
                    tracking_projects.append(
                        {
                            "Proyecto": project.get("name") or "",
                            "Score Inicial": project.get("viability_score") or 0,
                            "Performance Real": tracking["performance_score"],
                            "Eficiencia": tracking["efficiency_ratio"],
                        }
                    )

            if tracking_projects:
                df_tracking = pd.DataFrame(tracking_projects)

                fig_performance = px.scatter(
                    df_tracking,
                    x="Score Inicial",
                    y="Performance Real",
                    size="Eficiencia",
                    hover_data=["Proyecto"],
                    title=t("dashboard_initial_vs_real_performance"),
                    labels={
                        "Score Inicial": t("dashboard_initial_viability_score"),
                        "Performance Real": t("dashboard_real_performance_percent"),
                    },
                )

                # Línea de referencia (performance = score inicial)
                fig_performance.add_shape(
                    type="line",
                    x0=0,
                    y0=0,
                    x1=100,
                    y1=100,
                    line=dict(color="red", width=2, dash="dash"),
                    name="Línea de Referencia",
                )

                fig_performance.update_layout(height=400)
                st.plotly_chart(fig_performance, use_container_width=True)

                st.caption(t("dashboard_scatter_caption"))
    else:
        st.info("No hay datos de seguimiento post-implementación aún.")

    # Insights y recomendaciones
    st.subheader(t("dashboard_portfolio_insights"))

    insights = []

    # Análisis de scores
    high_score_projects = len(
        [p for p in projects if isinstance(p, dict) and _safe_number(p.get("viability_score")) >= 80]
    )
    if high_score_projects > 0 and total_projects > 0 and high_score_projects / total_projects > 0.5:
        insights.append(t("dashboard_insight_portfolio_solid"))

    # Análisis de complejidad
    high_complexity = len(
        [p for p in projects if isinstance(p, dict) and _safe_number(p.get("implementation_complexity")) >= 4]
    )
    if high_complexity > 0 and total_projects > 0 and high_complexity / total_projects > 0.3:
        insights.append(t("dashboard_insight_high_complexity"))

    # Análisis de ROI
    high_roi_projects = len(
        [p for p in projects if isinstance(p, dict) and _safe_number(p.get("roi_first_year")) >= 100]
    )
    if high_roi_projects > 0:
        insights.append(f"💰 **Excelente ROI**: {high_roi_projects} proyecto(s) con ROI superior al 100%")

    # Mostrar insights
    if insights:
        for insight in insights:
            st.info(insight)
    else:
        st.info(t("dashboard_add_more_for_insights"))

    # Exportar datos
    if st.button(t("dashboard_export_excel_btn")):
        st.info(
            "La exportación a Excel estará disponible una vez que se complete la migración completa a base de datos."
        )
