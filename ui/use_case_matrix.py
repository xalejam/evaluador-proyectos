"""UI de la pestana Use Case Matrix (vista de portafolio/priorizacion).

Flujo actual:
- La fuente de verdad para metadata/estado es `project_viability.db` (tabla `projects`).
- Los scores Impact/Effort se leen de `data/projects.db` (tabla `evaluations`, current).
- Esta vista NO crea proyectos ni captura evaluaciones; solo consume persistidos.
- La persistencia de estado desde esta vista actualiza `project_viability.db` y, si existe
  columna espejo en `data/projects.db.projects`, tambien la actualiza para consistencia.
"""

from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path
from typing import Iterable

import pandas as pd
import plotly.express as px
import streamlit as st

from domain.matrix import classify_quadrant
from infra.config_loader import ConfigLoader
from infra.db import DB_PATH as UCM_DB_PATH
from infra.db import init_db
from infra.db.connection import get_sqlite_conn as get_conn
from infra.db.migrations import ensure_projects_schema
from ui.tabs.shared import t
from ui.i18n_labels import label_status

PV_DB_PATH = "project_viability.db"
VALID_STATUSES = (
    "evaluated",
    "backlog",
    "on_hold",
    "approved",
    "in_agenda",
    "executing",
    "implemented",
    "rejected",
    "handed_off",
)
VALID_TEAMS = ("NOLA", "Brazil", "Champions", "Other")


def _get_ucm_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(UCM_DB_PATH.as_posix())
    conn.row_factory = sqlite3.Row
    return conn


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = ? LIMIT 1",
        (table_name,),
    ).fetchone()
    return row is not None


def _table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    if not _table_exists(conn, table_name):
        return set()
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row["name"] for row in rows}


def _add_column_if_missing(conn: sqlite3.Connection, table: str, column_def: str) -> None:
    col_name = column_def.strip().split()[0]
    if col_name not in _table_columns(conn, table):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column_def}")


def ensure_matrix_schema() -> None:
    """Migraciones idempotentes para la fuente consumida por matriz."""
    # Fuente de verdad portfolio
    with get_conn(PV_DB_PATH) as conn:
        ensure_projects_schema(conn)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_projects_project_id ON projects(project_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_projects_updated_at ON projects(updated_at)")
        conn.commit()

    # Espejo (opcional) para mantener consistencia visual/historica en data/projects.db
    init_db()
    with _get_ucm_conn() as conn:
        if _table_exists(conn, "projects"):
            _add_column_if_missing(conn, "projects", "status TEXT")
            _add_column_if_missing(conn, "projects", "delivery_team TEXT")
            _add_column_if_missing(conn, "projects", "loop_url TEXT")
            _add_column_if_missing(conn, "projects", "year INTEGER")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ucm_projects_status ON projects(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ucm_projects_year ON projects(year)")
            conn.commit()


def _load_current_scores_df() -> pd.DataFrame:
    with _get_ucm_conn() as conn:
        if not _table_exists(conn, "evaluations"):
            return pd.DataFrame(columns=["project_id", "impact_score", "effort_score", "eval_created_at"])
        sql = """
            SELECT e.project_id, e.impact_score, e.effort_score, e.created_at AS eval_created_at
            FROM evaluations e
            JOIN (
                SELECT project_id, MAX(created_at) AS max_created_at
                FROM evaluations
                WHERE is_current = 1
                GROUP BY project_id
            ) curr
              ON curr.project_id = e.project_id
             AND curr.max_created_at = e.created_at
            WHERE e.is_current = 1
        """
        return pd.read_sql_query(sql, conn)


def _load_portfolio_df() -> pd.DataFrame:
    with get_conn(PV_DB_PATH) as conn:
        cols = _table_columns(conn, "projects")
        id_expr = "project_id" if "project_id" in cols else "id"
        created_expr = "created_date" if "created_date" in cols else "created_at"
        updated_expr = "updated_at" if "updated_at" in cols else created_expr
        sql = f"""
            SELECT
                COALESCE(project_id, id) AS project_id,
                COALESCE(name, '') AS name,
                COALESCE(owner, '') AS owner,
                COALESCE(country, '') AS country,
                COALESCE(status, 'evaluated') AS status,
                COALESCE(delivery_team, '') AS delivery_team,
                COALESCE(loop_url, '') AS loop_url,
                COALESCE({updated_expr}, {created_expr}, '') AS updated_at,
                COALESCE(created_date, '') AS created_date,
                COALESCE(viability_score, 0) AS score_total
            FROM projects
            WHERE COALESCE({id_expr}, '') <> ''
        """
        df = pd.read_sql_query(sql, conn)

    if df.empty:
        return df

    # Solo estados relevantes al ciclo nuevo (si existen otros legacy, tambien se muestran)
    df["status"] = df["status"].fillna("evaluated").astype(str)

    dt_series = pd.to_datetime(df["updated_at"], errors="coerce")
    dt_series = dt_series.fillna(pd.to_datetime(df["created_date"], errors="coerce"))
    df["year"] = dt_series.dt.year.fillna(date.today().year).astype(int)

    scores = _load_current_scores_df()
    if not scores.empty:
        df = df.merge(scores[["project_id", "impact_score", "effort_score"]], on="project_id", how="left")
    else:
        df["impact_score"] = None
        df["effort_score"] = None

    return df


def _status_color_map(statuses: Iterable[str]) -> dict[str, str]:
    palette = {
        "evaluated": "#4e79a7",
        "backlog": "#f28e2b",
        "on_hold": "#edc948",
        "approved": "#59a14f",
        "in_agenda": "#59a14f",
        "executing": "#76b7b2",
        "implemented": "#2ca02c",
        "rejected": "#e15759",
        "handed_off": "#9c755f",
    }
    return {s: palette.get(s, "#7f7f7f") for s in statuses}


def _export_buttons(df: pd.DataFrame, prefix: str) -> None:
    if df.empty:
        return
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    json_bytes = df.to_json(orient="records", force_ascii=False, indent=2).encode("utf-8")
    c1, c2 = st.columns(2)
    with c1:
        st.download_button(t("download_csv"), csv_bytes, file_name=f"{prefix}.csv", mime="text/csv", key=f"{prefix}_csv")
    with c2:
        st.download_button(
            t("download_json"), json_bytes, file_name=f"{prefix}.json", mime="application/json", key=f"{prefix}_json"
        )


def update_status(project_id: str, new_status: str) -> None:
    """Actualiza estado en source of truth y espejo opcional."""
    with get_conn(PV_DB_PATH) as conn:
        conn.execute(
            """
            UPDATE projects
            SET status = ?, updated_at = datetime('now')
            WHERE id = ? OR project_id = ?
            """,
            (new_status, project_id, project_id),
        )
        conn.commit()

    # Espejo opcional
    with _get_ucm_conn() as conn:
        if _table_exists(conn, "projects") and "status" in _table_columns(conn, "projects"):
            conn.execute("UPDATE projects SET status = ? WHERE project_id = ?", (new_status, project_id))
            conn.commit()


def _render_scatter(df: pd.DataFrame, threshold_impact: float, threshold_effort: float) -> None:
    st.subheader(t("ucm_header"))
    if df.empty:
        st.info(t("ucm_no_saved_projects"))
        return

    plot_df = df.copy()
    plot_df = plot_df.dropna(subset=["impact_score", "effort_score"])
    if plot_df.empty:
        st.info(t("ucm_no_scores_filtered"))
        return

    plot_df["quadrant"] = plot_df.apply(
        lambda r: classify_quadrant(float(r["impact_score"]), float(r["effort_score"]), threshold_impact, threshold_effort),
        axis=1,
    )
    plot_df["label"] = plot_df["project_id"] + " - " + plot_df["name"].fillna("")

    fig = px.scatter(
        plot_df,
        x="effort_score",
        y="impact_score",
        color="status",
        color_discrete_map=_status_color_map(plot_df["status"].dropna().unique().tolist()),
        text="project_id",
        hover_data={
            "project_id": True,
            "name": True,
            "status": True,
            "score_total": True,
            "delivery_team": True,
            "loop_url": True,
        },
        title=t("ucm_header"),
    )
    fig.add_vline(x=threshold_effort, line_dash="dash", line_color="gray")
    fig.add_hline(y=threshold_impact, line_dash="dash", line_color="gray")
    fig.update_traces(textposition="top center")
    fig.update_xaxes(title="Effort Score", range=[0.8, 5.2], dtick=0.5)
    fig.update_yaxes(title="Impact Score", range=[0.8, 5.2], dtick=0.5)
    st.plotly_chart(fig, use_container_width=True)


def render_use_case_matrix_tab() -> None:
    """Renderiza la pestana Use Case Matrix como vista de portafolio."""
    st.header(t("ucm_header"))

    try:
        ensure_matrix_schema()
    except Exception as exc:
        st.error(f"{t('ucm_schema_init_error')}: {exc}")
        return

    cfg = ConfigLoader().load()
    threshold_impact = float(cfg["thresholds"]["impact"])
    threshold_effort = float(cfg["thresholds"]["effort"])

    try:
        base_df = _load_portfolio_df()
    except Exception as exc:
        st.error(f"{t('ucm_load_portfolio_error')}: {exc}")
        return

    if base_df.empty:
        st.info(t("ucm_no_saved_projects"))
        return

    current_year = date.today().year
    years = sorted(base_df["year"].dropna().astype(int).unique().tolist())
    default_year = current_year if current_year in years else (max(years) if years else current_year)

    filtered_base = base_df.copy()
    filtered_base["delivery_team_display"] = filtered_base["delivery_team"].fillna("").replace("", t("ucm_no_team"))

    c1, c2, c3, c4 = st.columns([1, 2, 2, 2])
    with c1:
        year_filter = st.selectbox(t("ucm_year_filter"), options=years if years else [default_year], index=(years.index(default_year) if years else 0))
    with c2:
        team_options = sorted(set(filtered_base["delivery_team_display"].tolist()))
        team_filter = st.multiselect(t("ucm_team_filter"), options=team_options, default=team_options)
    with c3:
        status_options = list(dict.fromkeys(base_df["status"].astype(str).tolist() + list(VALID_STATUSES)))
        status_option_labels = [label_status(s) for s in status_options]
        status_map = {label_status(code): code for code in status_options}
        selected_labels = st.multiselect(t("ucm_status_filter"), options=status_option_labels, default=status_option_labels)
        status_filter = [status_map[lbl] for lbl in selected_labels]
    with c4:
        text_filter = st.text_input(t("ucm_search_filter"))

    filtered = filtered_base.copy()
    filtered = filtered[filtered["year"] == int(year_filter)]
    if team_filter:
        filtered = filtered[filtered["delivery_team_display"].isin(team_filter)]
    if status_filter:
        filtered = filtered[filtered["status"].isin(status_filter)]
    if text_filter.strip():
        q = text_filter.strip().lower()
        filtered = filtered[
            filtered["name"].astype(str).str.lower().str.contains(q, na=False)
            | filtered["owner"].astype(str).str.lower().str.contains(q, na=False)
            | filtered["project_id"].astype(str).str.lower().str.contains(q, na=False)
        ]

    _render_scatter(filtered, threshold_impact, threshold_effort)

    st.subheader(t("ucm_detail_title"))
    if filtered.empty:
        st.info(t("ucm_no_detail_results"))
        return

    options = {f"{r.project_id} - {r.name}": r.project_id for r in filtered.itertuples(index=False)}
    selected_label = st.selectbox(t("ucm_select_project"), options=list(options.keys()), key="ucm_portfolio_selected")
    selected_project_id = options[selected_label]
    detail = filtered[filtered["project_id"] == selected_project_id].iloc[0]

    d1, d2 = st.columns([2, 1])
    with d1:
        st.write(f"**Project ID:** `{detail['project_id']}`")
        st.write(f"**Nombre:** {detail['name']}")
        st.write(f"**Estado:** {label_status(str(detail['status']))}")
        st.write(f"**Delivery team:** {detail.get('delivery_team', '') or 'N/D'}")
        st.write(f"**Impact score:** {detail.get('impact_score') if pd.notna(detail.get('impact_score')) else 'N/D'}")
        st.write(f"**Effort score:** {detail.get('effort_score') if pd.notna(detail.get('effort_score')) else 'N/D'}")
        st.write(f"**Score total:** {detail.get('score_total', 'N/D')}")
        if detail.get("loop_url"):
            st.link_button(t("open_loop_btn"), str(detail["loop_url"]))

    with d2:
        if st.button(t("ucm_open_viability_btn"), key=f"ucm_open_viab_{selected_project_id}"):
            st.session_state.selected_project_id = selected_project_id
            st.session_state.edit_mode = True
            st.info(t("ucm_open_viability_hint"))

        change_options = list(VALID_STATUSES)
        curr_status = str(detail.get("status") or "evaluated")
        idx = change_options.index(curr_status) if curr_status in change_options else 0
        new_status_labels = [label_status(s) for s in change_options]
        current_label = label_status(curr_status)
        idx_label = new_status_labels.index(current_label) if current_label in new_status_labels else 0
        selected_new_label = st.selectbox(t("ucm_change_status"), options=new_status_labels, index=idx_label, key=f"ucm_status_{selected_project_id}")
        reverse_status = {label_status(code): code for code in change_options}
        new_status = reverse_status[selected_new_label]
        if st.button(t("ucm_save_status_btn"), key=f"ucm_save_status_{selected_project_id}"):
            try:
                update_status(selected_project_id, new_status)
                st.success(f"{t('ucm_status_updated')} '{new_status}'.")
                st.rerun()
            except Exception as exc:
                st.error(f"{t('ucm_status_update_error')}: {exc}")

    st.subheader(t("ucm_filtered_dataset"))
    export_cols = [
        "project_id",
        "name",
        "owner",
        "country",
        "status",
        "delivery_team_display",
        "delivery_team",
        "year",
        "score_total",
        "impact_score",
        "effort_score",
        "loop_url",
        "updated_at",
    ]
    export_df = filtered[[c for c in export_cols if c in filtered.columns]].copy()
    if "delivery_team_display" in export_df.columns:
        export_df = export_df.rename(columns={"delivery_team_display": "delivery_team_label"})
    st.dataframe(export_df, use_container_width=True, hide_index=True)
    _export_buttons(export_df, prefix="use_case_matrix_filtrado")
