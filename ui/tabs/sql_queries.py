"""
Pestana para ejecutar consultas SQL de solo lectura sobre SQLite.
"""

import io
import re
import sqlite3
from pathlib import Path
import pandas as pd
import streamlit as st
from ui.tabs.shared import t

FORBIDDEN_SQL = [
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "create",
    "replace",
    "truncate",
    "attach",
    "detach",
    "pragma",
    "vacuum",
    "reindex",
    "begin",
    "commit",
    "rollback",
]


def _normalize_query(query: str) -> str:
    normalized = query.strip()
    if normalized.endswith(";"):
        normalized = normalized[:-1].strip()
    return normalized


def _validate_readonly_query(query: str):
    q = _normalize_query(query)
    if not q:
        return False, t("sql_error_empty")

    # Evitar múltiples sentencias.
    if ";" in q:
        return False, t("sql_error_single_statement")

    lowered = q.lower()
    if not (lowered.startswith("select") or lowered.startswith("with")):
        return False, t("sql_error_readonly")

    for keyword in FORBIDDEN_SQL:
        if re.search(rf"\b{keyword}\b", lowered):
            return False, f"{t('sql_error_forbidden_keyword')} {keyword.upper()}."

    return True, ""


def render_sql_queries_tab():
    st.header(t("sql_tab_header"))
    st.caption(t("sql_tab_caption"))

    st.markdown(t("sql_available_tables_markdown"))

    default_query = (
        "SELECT id, name, priority, viability_score, status\n"
        "FROM projects\n"
        "ORDER BY created_date DESC\n"
        "LIMIT 50"
    )
    query = st.text_area(t("sql_query_input_label"), value=default_query, height=180)

    col_run, col_clear = st.columns([1, 1])
    with col_run:
        run = st.button(t("sql_run_select_btn"), type="primary", use_container_width=True)
    with col_clear:
        clear = st.button(t("sql_clear_btn"), use_container_width=True)

    if clear:
        st.rerun()

    if not run:
        return

    ok, message = _validate_readonly_query(query)
    if not ok:
        st.error(message)
        return

    try:
        db_path = st.session_state.excel_manager.db_path
        db_uri = Path(db_path).as_uri() + "?mode=ro"
        with sqlite3.connect(db_uri, uri=True) as conn:
            df = pd.read_sql_query(_normalize_query(query), conn)
    except Exception as e:
        st.error(f"{t('sql_error_running_query')}: {e}")
        return

    st.success(f"{t('sql_query_ok_rows')} {len(df)}")
    st.dataframe(df, use_container_width=True, hide_index=True)

    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label=t("sql_download_csv_btn"), data=io.BytesIO(csv_bytes), file_name="sql_result.csv", mime="text/csv"
    )
